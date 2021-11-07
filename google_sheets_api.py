import httplib2
import time

import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials


class GoogleSheetsApi:
    def __init__(self, token):
        self.auth_service = None
        self.request_count = 0
        self.request_limit = 60
        self.request_sleep = 200
        self.authorization(token)


    # Authorisation in serves google
    # Accept: authorisation token
    def authorization(self, token):
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            token,
            ['https://www.googleapis.com/auth/spreadsheets'])
        http_auth = credentials.authorize(httplib2.Http())
        self.auth_service = apiclient.discovery.build('sheets', 'v4', http=http_auth)
        self.request_count += 1

    # Get data from document table_id, sheet list_name in range [start_range_point, end_range_point]
    # Return: mas with data with major_dimension (ROWS/COLUMNS)
    def get_data_from_sheets(self, table_id, list_name, start_range_point, end_range_point, major_dimension):
        self.request_count += 1
        if self.request_count >= self.request_limit:
            self.request_count = 0
            time.sleep(self.request_sleep)

        values = self.auth_service.spreadsheets().values().get(
            spreadsheetId=table_id,
            range="'{0}'!{1}:{2}".format(list_name, start_range_point, end_range_point),
            majorDimension=major_dimension
        ).execute()
        if 'values' in values.keys():
            return values['values']
        else:
            return []

    # Put data to document table_id, sheet list_name in range [start_range_point, end_range_point]
    # in major_dimension (ROWS/COLUMNS)
    def put_data_to_sheets(self, table_id, list_name, start_range_point, end_range_point, major_dimension, data):
        self.request_count += 1
        print(self.request_count)
        if self.request_count >= self.request_limit:
            self.request_count = 0
            print('sleep')
            time.sleep(self.request_sleep)

        values = self.auth_service.spreadsheets().values().batchUpdate(
            spreadsheetId=table_id,
            body={
                "valueInputOption": "USER_ENTERED",
                "data": [{
                    "range": ("{0}!{1}:{2}".format(list_name, start_range_point, end_range_point)),
                    "majorDimension": major_dimension,
                    "values": data
                }]
            }).execute()

    # Put data to document table_id, sheet list_name in column column(char) and range [start_row, start_row+len(data)]
    def put_column_to_sheets(self, table_id, list_name, column, start_row, data):
        values = [[i] for i in data]
        self.put_data_to_sheets(table_id, list_name, column + str(start_row),
                           column + str(start_row+len(data)), 'ROWS', values)

    # Put data to document table_id, sheet list_name in column column(char) and range [start_row, start_row+len(data)]
    # by packets with size packet_size
    def put_column_to_sheets_packets(self, table_id, list_name, column, start_row, data, packet_size):
        # Division data from pakets
        def func_chunks_generators(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i: i + n]
        packets = list(func_chunks_generators(data, packet_size))

        shift = 0
        for packet in packets:
            self.put_column_to_sheets(table_id, list_name, column, start_row+shift, packet)
            shift += packet_size

    # Put data to document table_id, sheet list_name in row column and
    # range [start_column(char), start_column+len(data)]
    def put_row_to_sheets(self, table_id, list_name, row, start_column, data):
        values = [[i] for i in data]
        end_column = self.convert_column_index_to_int(start_column) + len(data)
        end_column = self.convert_column_index_to_char(end_column)
        self.put_data_to_sheets(table_id, list_name, start_column + str(row), end_column + str(row), 'COLUMNS', values)

    # Get sheet_id of list_name in document table_id"""
    def get_sheet_id(self, table_id, list_name):
        self.request_count += 1
        if self.request_count >= self.request_limit:
            self.request_count = 0
            time.sleep(self.request_sleep)
        spreadsheet = self.auth_service.spreadsheets().get(spreadsheetId=table_id).execute()
        sheet_id = None
        for _sheet in spreadsheet['sheets']:
            if _sheet['properties']['title'] == list_name:
                sheet_id = _sheet['properties']['sheetId']
        return sheet_id

    # Generate spreadsheets request for colorizing range in table
    # Accept: document table_id, sheet list_name, start_column(int), start_row(int), end_column(int), end_row(int)
    #   color([r,g,b,a] r,g,b,a = [0;1])
    def gen_colorizing_range_request(self, table_id, list_name, start_column, start_row, end_column,
                                     end_row, color):
        return {
            "repeatCell": {
                "range": {
                    "sheetId": self.get_sheet_id(table_id, list_name),
                    "startRowIndex": start_row - 1,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_column - 1,
                    "endColumnIndex": end_column
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {
                            "red": color[0],
                            "green": color[1],
                            "blue": color[2]
                        }
                    }
                },
                "fields": "userEnteredFormat.backgroundColor"
            }
        }

    # Generate spreadsheets request for auto resize columns
    def gen_auto_resize_column_request(self, table_id, list_name, start_column, end_column):
        return {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": self.get_sheet_id(table_id, list_name),
                    "dimension": "COLUMNS",
                    "startIndex": start_column - 1,
                    "endIndex": end_column
                }
            }
        }

    # Apply spreadsheets requests on document table_id
    def apply_spreadsheets_requests(self, table_id, requests):
        self.request_count += 1
        if self.request_count >= self.request_limit:
            self.request_count = 0
            time.sleep(self.request_sleep)
        self.auth_service.spreadsheets().batchUpdate(
            spreadsheetId=table_id,
            body={"requests": [requests]}).execute()

    # Clear sheet list_name in document table_id
    def clear_sheet(self, table_id, list_name):
        self.request_count += 1
        if self.request_count >= self.request_limit:
            self.request_count = 0
            time.sleep(self.request_sleep)
        range_all = '{0}!A1:Z'.format(list_name)
        self.auth_service.spreadsheets().values().clear(spreadsheetId=table_id, range=range_all, body={}).execute()

    # Get sizes of sheet list_name in document table_id"""
    # Return [column_count, row_count]
    def get_list_size(self, table_id, list_name):
        self.request_count += 1
        if self.request_count >= self.request_limit:
            self.request_count = 0
            time.sleep(self.request_sleep)
        request = self.auth_service.spreadsheets().get(spreadsheetId=table_id, ranges=list_name).execute()
        return [request['sheets'][0]['properties']['gridProperties']['columnCount'],
                request['sheets'][0]['properties']['gridProperties']['rowCount']]

    # Convert char column_index to int
    # Accept: char column_index
    # Return: int column_index
    @staticmethod
    def convert_column_index_to_int(char_column_index):
        char_column_index = char_column_index.lower()
        int_index = 0
        len_ = len(char_column_index)-1
        for i in range(len_, -1, -1):
            digit = ord(char_column_index[i]) - ord('a') + 1
            int_index += digit * pow(26, len_ - i)

        return int_index

    # Convert int column_index to char
    # Accept: int column_index
    # Return: char column_index
    @staticmethod
    def convert_column_index_to_char(int_column_index):
        char_column_index = ''
        while int_column_index != 0:
            char_column_index += chr(ord('A') + int_column_index % 26 - 1)
            int_column_index //= 26

        return char_column_index[::-1]
