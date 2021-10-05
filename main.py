from sites_generator import SitesGenerator

"""Options"""
TOKEN_FILE = 'token.json'                                    # File with google service auth token.
TABLE_ID = '1mZb-JiEzSSqyxXsQeuo1NpentUqDSJLkzDkgqLE3Vy4'    # ID Google Sheets document
REVIEWS_CSV_FILE = 'goods.csv'                               # Path/name.csv of goods file
OUT_DIRECTORY = 'S:\\sites\\'                                # Path of output directory

generator = SitesGenerator(REVIEWS_CSV_FILE)
generator.download_data(TOKEN_FILE, TABLE_ID)
generator.gen_sites(TOKEN_FILE, TABLE_ID, OUT_DIRECTORY)
