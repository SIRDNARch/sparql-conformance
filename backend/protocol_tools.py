import telnetlib as telnet
import re
from typing import Tuple

from backend.models import TestObject, FAILED, PASSED, RESULTS_NOT_THE_SAME
from backend.rdf_tools import compare_ttl


def prepare_request(test: TestObject, request_with_reponse: str, newpath: str) -> Tuple[str, str]:
    request = request_with_reponse.split('#### Response')[0]
    # Quick fix: change the x-www-url-form-urlencoded content type to x-www-form-urlencoded
    request = request.replace('application/x-www-url-form-urlencoded', 'application/x-www-form-urlencoded')
    if test.type_name == 'GraphStoreProtocolTest':
        request = request.replace(
            '$HOST$', test.config.HOST)
        request = request.replace(
            '$GRAPHSTORE$', test.config.GRAPHSTORE)
        request = request.replace(
            '$NEWPATH$', newpath)
    before_header = True
    request_lines = request.splitlines()
    index_header = 0
    index_line_between = 0
    for index, line in enumerate(request_lines):
        line = line.strip()
        request_lines[index] = line
        if not line and not before_header and index_line_between == 0:
            index_line_between = index
        if line.startswith('POST') or line.startswith('GET') or line.startswith(
                'PUT') or line.startswith('DELETE') or line.startswith('HEAD'):
            before_header = False
            index_header = index
        if line.startswith('GET') and not line.endswith('HTTP/1.1'):
            request_lines[index] = line + ' HTTP/1.1'
    request_header_lines = request_lines[index_header:index_line_between]
    request_body_lines = [
        x for x in request_lines[index_line_between + 1:] if x]
    request_header = '\r\n'.join(request_header_lines)
    request_body = '\r\n'.join(request_body_lines)
    request_header = request_header.replace('XXX', str(len(request_body)))
    request_header = request_header + '\r\n' + 'Authorization: Bearer abc'
    return request_header + '\r\n\r\n', request_body + '\r\n'


def prepare_response(request_with_reponse: str) -> dict[str, str | list[str]]:
    response: dict[str, str | list[str]] = {'status_codes': [], 'content_types': []}
    response_string = request_with_reponse.split('#### Response')[1]
    response_lines = [x.strip() for x in response_string.splitlines() if x]
    for line in response_lines:
        if line.endswith('response') or re.search(r'\dxx', line) is not None:
            line = line.replace('response', '')
            status_codes = line.strip().split('or')
            for status_code in status_codes:
                response['status_codes'].append(status_code.strip())
        if re.search(r'^\d\d\d ', line) is not None:
            response['status_codes'].append(
                re.search(r'^\d\d\d ', line).group(0))
        if line.startswith('Content-Type:'):
            line = line.replace('Content-Type:', '')
            content_types = line.strip().split('or')
            for content_type in content_types:
                # Split on ',' to handle multiple content types
                cts = content_type.split(',')
                for ct in cts:
                    if ct != '':
                        response['content_types'].append(ct.strip().split(';')[0])
        if line.startswith('true'):
            response['result'] = 'true'
        if line.startswith('false'):
            response['result'] = 'false'
        if line.startswith('Location: $NEWPATH$'):
            response['newpath'] = 'Location: $NEWPATH$'
    if 'text/turtle' in response['content_types'] and response.get(
            'result') is None:
        response['result'] = '\n\n'.join(response_string.split('\n\n')[2:])
    return response


def compare_response(expected_response: dict[str, str | list[str]], got_response: str) -> Tuple[bool, str]:
    status_code_match = False
    content_type_match = False
    result_match = False

    for status_code in expected_response['status_codes']:
        pattern = r'HTTP/1\.1 '
        for digit in status_code:
            if digit == 'x':
                pattern += '\\d'
            else:
                pattern += digit
        found_status_code = re.search(pattern, got_response)
        if found_status_code is not None:
            status_code_match = True

    if len(expected_response['content_types']) == 0:
        content_type_match = True

    for content_type in expected_response['content_types']:
        if got_response.find(content_type) != -1:
            content_type_match = True

    if expected_response.get('result') is None or got_response.find(
            expected_response['result']) != -1:
        result_match = True
    if 'text/turtle' in expected_response.get(
            'content_types') and status_code_match and content_type_match:
        response_ttl = '\n\n'.join(got_response.split('\n\n')[1:])
        status, error_type, expected_string, query_string, expected_string_red, query_string_red = compare_ttl(
            expected_response['result'], response_ttl)
        if status == 'Passed':
            result_match = True
    newpath = ''
    if 'newpath' in expected_response:
        match = re.search(r'^Location:\s*(.*)', got_response, re.MULTILINE)
        if match:
            newpath = match.group(1)
    return status_code_match and content_type_match and result_match, newpath


def run_protocol_test(
        test: TestObject,
        test_protocol: str,
        newpath: str) -> tuple:
    server_address = 'localhost'
    port = test.config.port
    result = FAILED
    error_type = RESULTS_NOT_THE_SAME
    status = []
    if 'followed by' in test_protocol:
        test_request_split = test_protocol.split('followed by')
    elif test_protocol.count('#### Request') > 1:
        test_request_split = [line for line in test_protocol.split(
            '#### Request') if len(line) > 2]
    else:
        test_request_split = [test_protocol]
    requests = []
    responses = []
    got_responses = []
    for request_with_reponse in test_request_split:
        request_head, request_body = prepare_request(test, request_with_reponse, newpath)
        requests.append(request_head + request_body)
        response = prepare_response(request_with_reponse)
        responses.append(response)
        tn = telnet.Telnet(server_address, int(port))
        if 'charset=UTF-16' in request_head:
            encoding = 'utf-16'
        else:
            encoding = 'utf-8'
        tn.write(request_head.encode('utf-8') + request_body.encode(encoding))
        tn_response = tn.read_all().decode('utf-8')
        got_responses.append(tn_response)
        matching, newpath = compare_response(response, tn_response)
        status.append(matching)
        tn.close()
    if all(status):
        result = PASSED
        error_type = ''
    extracted_expected_responses = ''
    for response in responses:
        extracted_expected_responses += str(response) + '\n'
    extracted_sent_requests = ''
    for request in requests:
        extracted_sent_requests += request + '\n'
    got_responses_string = ''
    for response in got_responses:
        got_responses_string += response + '\n'
    return result, error_type, extracted_expected_responses, extracted_sent_requests, got_responses_string, newpath
