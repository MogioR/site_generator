import random
import os
import json
import time
from multiprocessing import Pool
from functools import partial

import pandas as pd
from tqdm import tqdm

from google_sheets_api import GoogleSheetsApi
from bs4 import BeautifulSoup
from russian_names import RussianNames


"""List names for downloading"""
CONTAINER_LIST = 'Container'
MASTER_DATA_LIST = 'MasterData'
MASTER_ABOUT_LIST = 'MasterAbout'
SELECTION_MASTER_LIST = 'SectionMaster'
MASTER_EDUCATION = 'MasterEducation'

MASTER_MINIMUM_COUNT = 6
MASTER_MAXIMUM_COUNT = 14

NUM_THREADS = 8


class SitesGenerator:
    def __init__(self, reviews_csv_file):
        self.container_df = pd.DataFrame()
        self.master_data_df = pd.DataFrame()
        self.master_about_df = pd.DataFrame()
        self.selection_master_df = pd.DataFrame()
        self.master_education_df = pd.DataFrame()
        self.review_df = pd.DataFrame()

        self.master_maximum_count = MASTER_MAXIMUM_COUNT
        self.master_minimum_count = MASTER_MINIMUM_COUNT

        self.progress_bar = None

        # Load reviews
        if not os.path.exists(reviews_csv_file):
            print('Bad path to goods_bd file!')
            raise Exception('Bad path to goods_bd file!')

        self.reviews_csv_file = reviews_csv_file
        self.review_df = pd.read_csv(reviews_csv_file, sep='\t')
        self.review_df = self.review_df.sample(frac=1).reset_index(drop=True)
        self.review_df['used'] = 0.0

    def download_data(self, token, table_id):
        # Downloading data from sheets
        sheets = GoogleSheetsApi(token)
        container_data = sheets.get_data_from_sheets(table_id, CONTAINER_LIST, 'A2',
                                'O' + str(sheets.get_list_size(table_id, CONTAINER_LIST)[1]), 'COLUMNS')
        master_data_data = sheets.get_data_from_sheets(table_id, MASTER_DATA_LIST, 'A2',
                                'O' + str(sheets.get_list_size(table_id, MASTER_DATA_LIST)[1]), 'COLUMNS')
        master_about_data = sheets.get_data_from_sheets(table_id, MASTER_ABOUT_LIST, 'A2',
                                'C' + str(sheets.get_list_size(table_id, MASTER_ABOUT_LIST)[1]), 'COLUMNS')
        selection_master_data = sheets.get_data_from_sheets(table_id, SELECTION_MASTER_LIST, 'A2',
                                'B' + str(sheets.get_list_size(table_id, SELECTION_MASTER_LIST)[1]), 'COLUMNS')
        master_education_data = sheets.get_data_from_sheets(table_id, MASTER_EDUCATION, 'A2',
                                'B' + str(sheets.get_list_size(table_id, MASTER_EDUCATION)[1]), 'COLUMNS')

        # Data frame filling
        elements_count = len(container_data[0])
        self.container_df['sectionId'] = container_data[0]
        self.container_df['location'] = self.expand_list(container_data[1], elements_count)
        self.container_df['urlPath'] = self.expand_list(container_data[2], elements_count)
        self.container_df['name'] = self.expand_list(container_data[3], elements_count)
        self.container_df['masterList'] = self.expand_list(container_data[4], elements_count)
        self.container_df['title'] = self.expand_list(container_data[5], elements_count)
        self.container_df['description'] = self.expand_list(container_data[6], elements_count)
        self.container_df['question_1'] = self.expand_list(container_data[7], elements_count)
        self.container_df['answer_1'] = self.expand_list(container_data[8], elements_count)
        self.container_df['question_2'] = self.expand_list(container_data[9], elements_count)
        self.container_df['answer_2'] = self.expand_list(container_data[10], elements_count)
        self.container_df['question_3'] = self.expand_list(container_data[11], elements_count)
        self.container_df['answer_3'] = self.expand_list(container_data[12], elements_count)
        self.container_df['add'] = self.to_bool_list(self.expand_list(container_data[13], elements_count))
        self.container_df['First_add'] = self.to_bool_list(self.expand_list(container_data[14], elements_count))
        self.container_df['generated'] = self.expand_list([False], elements_count)

        elements_count = len(master_data_data[0])
        self.master_data_df['path'] = master_data_data[0]
        self.master_data_df['initials'] = self.expand_list(master_data_data[1], elements_count)
        self.master_data_df['logoPath'] = self.expand_list(master_data_data[2], elements_count)
        self.master_data_df['rate'] = self.expand_list(master_data_data[3], elements_count)
        self.master_data_df['amount_reviews'] = self.expand_list(master_data_data[4], elements_count)
        self.master_data_df['amount_lessons'] = self.expand_list(master_data_data[5], elements_count)
        self.master_data_df['cost_time'] = self.expand_list(master_data_data[6], elements_count)
        self.master_data_df['work_online'] = self.to_bool_list(self.expand_list(master_data_data[7], elements_count))
        self.master_data_df['consultation'] = self.to_bool_list(self.expand_list(master_data_data[8], elements_count))
        self.master_data_df['under_school'] = self.to_bool_list(self.expand_list(master_data_data[9], elements_count))
        self.master_data_df['junior_school'] = self.to_bool_list(self.expand_list(master_data_data[10], elements_count))
        self.master_data_df['middle_school'] = self.to_bool_list(self.expand_list(master_data_data[11], elements_count))
        self.master_data_df['high_school'] = self.to_bool_list(self.expand_list(master_data_data[12], elements_count))
        self.master_data_df['students'] = self.to_bool_list(self.expand_list(master_data_data[13], elements_count))
        self.master_data_df['adults'] = self.to_bool_list(self.expand_list(master_data_data[14], elements_count))

        elements_count = len(master_about_data[0])
        self.master_about_df['id'] = master_about_data[0]
        self.master_about_df['masterDataId'] = self.expand_list(master_about_data[1], elements_count)
        self.master_about_df['aboutText'] = self.expand_list(master_about_data[2], elements_count)

        elements_count = len(selection_master_data[0])
        self.selection_master_df['sectionId'] = selection_master_data[0]
        self.selection_master_df['pathMaster'] = self.expand_list(selection_master_data[1], elements_count)

        elements_count = len(master_education_data[0])
        self.master_education_df['masterDataId'] = master_education_data[0]
        self.master_education_df['education'] = self.expand_list(master_education_data[1], elements_count)

    def expand_list(self, arr, size, placeholder=''):
        return arr + ([placeholder]*(size-len(arr)))

    def to_bool_list(self, arr):
        return [True if len(i) > 0 else False for i in arr]

    def gen_sites(self, token, table_id, out_directory):
        # Generate sites
        print('Generate first sites')
        firsts_sites = self.container_df[self.container_df['First_add'] == True].values
        start = time.time()
        self.gen_sites_by_list_fast4(out_directory, firsts_sites)
        print('Time: ', time.time()-start)

        print('Generate not firsts sites')
        start = time.time()
        not_firsts_sites = self.container_df[self.container_df['First_add'] == False].values
        self.gen_sites_by_list_fast4(out_directory, not_firsts_sites)
        print('Time: ', time.time() - start)

        # Link sites
        print('Link sites')
        generated_sites = self.container_df[self.container_df['generated'] == True].values
        for site in tqdm(generated_sites):
            self.link_site(out_directory, site)
            self.container_df.loc[self.container_df['urlPath'] == site[2], 'add'] = True

        print('Mapping sites')
        # Mapping sites
        map_text = '<?xml version="1.0" encoding="UTF-8"?>\n' \
                   '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        map_text += self.gen_site_map_block('https://dumkii.com/')
        for site in tqdm(generated_sites):
            map_text += self.gen_site_map_block('https://dumkii.com/'+site[2])
        map_text += '</urlset>'

        with open(out_directory + 'sitemap.xml', 'w', encoding='utf-8') as f:
            f.write(map_text)

        # Mark added sites in google table
        print('Mark added sites in google table')
        sheets = GoogleSheetsApi(token)
        add_list = self.container_df['add'].tolist()
        add_list = ['add' if item else '' for item in add_list]
        sheets.put_column_to_sheets(table_id, CONTAINER_LIST, 'N', 2, len(add_list) + 2, add_list)

    def gen_sites_by_list(self, out_directory, sites):
        for site in sites:
            self.gen_site(out_directory, site)

    def gen_sites_by_list_fast4(self, out_directory, sites):
        selection_id_black_list = []

        # Gen master paths parallel
        pool = Pool(NUM_THREADS)
        func = partial(self.get_masters_paths, self.master_minimum_count, self.master_maximum_count)
        sites_masters = []
        for masters in tqdm(pool.imap_unordered(func, sites), total=len(sites)):
            sites_masters.append(masters)

        # Gen reviews one-thread
        sites_reviews = []
        for i in tqdm(range(len(sites))):
            if len(sites_masters[i]) != 0 and sites[i][0] not in selection_id_black_list:
                reviews_buf = self.get_reviews(self.master_minimum_count, len(sites_masters[i]), sites[i][0])
                sites_reviews.append(reviews_buf)
                if len(reviews_buf) == 0:
                    selection_id_black_list.append(sites[i][0])
            else:
                sites_reviews.append([])

        # Gen sites parallel
        func = partial(self.gen_site_fast, out_directory)
        func_args = []
        for i in range(len(sites)):
            func_args.append([sites[i], sites_masters[i], sites_reviews[i]])

        for _ in tqdm(pool.imap_unordered(func, func_args), total=len(func_args)):
            pass

    def gen_site(self, out_directory, site):
        masters = self.get_masters_paths(self.master_minimum_count, self.master_maximum_count, site)
        reviews = self.get_reviews(self.master_minimum_count, len(masters), site[0])

        if len(reviews) > 0:
            # Generate site text
            site_text = self.gen_site_code(site, masters, reviews)
            # Save site
            with open(out_directory + site[2] + '.html', 'w', encoding='utf-8') as f:
                f.write(site_text)
            # Mark generated
            self.container_df.loc[self.container_df['urlPath'] == site[2], 'generated'] = True

    def gen_site_fast(self, out_directory, args):
        site = args[0]
        masters = args[1]
        reviews = args[2]
        if len(reviews) > 0:
            # Generate site text
            site_text = self.gen_site_code(site, masters, reviews)
            # Save site
            with open(out_directory + site[2] + '.html', 'w', encoding='utf-8') as f:
                f.write(site_text)
            # Mark generated
            self.container_df.loc[self.container_df['urlPath'] == site[2], 'generated'] = True

    def link_site(self, out_directory, site):
        # Open site
        with open(out_directory+site[2]+'.html', 'r', encoding='utf-8') as f:
            site_text = f.read()
        site_item = BeautifulSoup(site_text, "html.parser")

        # Online block
        online_list = list(self.container_df.loc[(self.container_df.generated == True) &\
            (self.container_df.location == 'online') & (self.container_df.urlPath != site[2])]\
            [['urlPath', 'name']].values)

        if len(online_list) > 10:
            online_list = random.sample(online_list, 10)

        online_block = site_item.find('div', {'data-mark': "Container.linksBlock_1"}).parent.ul

        for i in range(len(online_list)):
            new_tag = site_item.new_tag('li')
            new_tag2 = site_item.new_tag('a', href='/'+online_list[i][0])
            online_block.append(new_tag)
            online_block.find_all('li')[-1].append(new_tag2)
            online_block.find_all('a')[-1].string = online_list[i][1]

        # Local block
        local_list = list(self.container_df.loc[(self.container_df.generated == True) &\
            (self.container_df.location != 'online') & (self.container_df.urlPath != site[2])]\
            [['urlPath', 'name']].values)

        if len(local_list) > 10:
            local_list = random.sample(local_list, 10)

        locale_block = site_item.find('div', {'data-mark': "Container.linksBlock_2"}).parent.ul

        for i in range(len(local_list)):
            new_tag = site_item.new_tag('li')
            new_tag2 = site_item.new_tag('a', href='/' + local_list[i][0])
            locale_block.append(new_tag)
            locale_block.find_all('li')[-1].append(new_tag2)
            locale_block.find_all('a')[-1].string = local_list[i][1]

        # Save site
        with open(out_directory + site[2] + '.html', 'w', encoding='utf-8') as f:
            f.write(str(site_item))

    def gen_site_code(self, site_data, masters, reviews):
        # Get template of site
        with open('template.html', 'r', encoding='utf-8') as f:
            site_text = f.read()
        site_item = BeautifulSoup(site_text, "html.parser")

        # Filling template
        # Info
        site_item.head.title.string = site_data[5]
        site_item.find('meta', {'data-mark': 'Container.description'}).attrs['content'] = site_data[6]
        site_item.find('h1', {'data-mark': 'Container.name'}).string = site_data[3]

        # Master list
        site_item.find('h2', {'data-mark': 'Container.masterList'}).string = site_data[4]
        masters_block = site_item.find('h2', {'data-mark': 'Container.masterList'}).parent.div

        min_len = min(len(masters), len(reviews))
        for i in range(min_len):
            master_item = self.gen_master_item(masters[i], reviews[i], i)
            if master_item is not None:
                masters_block.insert(i, master_item)

        # Questions
        site_item.find('h3', {'data-mark': 'Container.question_1'}).string = site_data[7]
        site_item.find('h3', {'data-mark': 'Container.question_2'}).string = site_data[9]
        site_item.find('h3', {'data-mark': 'Container.question_3'}).string = site_data[11]
        site_item.find('div', {'data-mark': 'Container.answer_1'}).string = site_data[8]
        site_item.find('div', {'data-mark': 'Container.answer_2'}).string = site_data[10]
        site_item.find('div', {'data-mark': 'Container.answer_3'}).string = site_data[12]
        site_item.find('script', {'type': 'application/ld+json'}).string = self.get_questions_script(site_data)

        new_tag = site_item.new_tag('script')
        site_item.body.append(new_tag)
        site_item.find_all('script')[-1]['type'] = 'application/ld+json'
        site_item.find_all('script')[-1].string = self.get_end_script(site_data[3], site_data[2]+'.html')

        return self.get_html(site_item)

    # Getting reviews equal selection_id from review_df, if reviews count less then minimum_reviews return [],
    # if count more then maximum_reviews return maximum_reviews reviews
    def get_reviews(self, minimum_reviews, maximum_reviews, selection_id):
        review_buf_df = self.review_df[(self.review_df.sectionId == selection_id) &
                                       (self.review_df.used == 0.0)].head(maximum_reviews)
        count_reviews = len(review_buf_df.index)
        if count_reviews < minimum_reviews:
            reviews_list = []
        else:
            self.review_df.at[review_buf_df.index, 'used'] = 1.0
            reviews_list = list(review_buf_df['review'].tolist())

        return reviews_list

    # Getting masters paths equal selection_id from selection_master_df
    # if masters count less then minimum_masters return [],
    # if count more then maximum_masters return maximum_masters masters
    def get_masters_paths(self, minimum_masters, maximum_masters, site):
        master_paths = self.selection_master_df[self.selection_master_df['sectionId'] == site[0]]['pathMaster']\
            .values
        master_paths = list(filter(lambda x: self.valid_master_path(x), master_paths))

        if len(master_paths) > maximum_masters:
            master_paths = random.sample(master_paths, maximum_masters)
        if len(master_paths) < minimum_masters:
            master_paths = []

        return master_paths

    # Validate master_path
    # If count masters with master_path equal 1 return True, else False
    def valid_master_path(self, master_path):
        masters_count = self.master_data_df[self.master_data_df['path'] == master_path].values
        return len(masters_count) == 1

    def gen_site_map_block(self, site_path):
        return '<url>\n<loc>'+site_path+'</loc>\n<changefreq>weekly</changefreq>\n<priority>1.00</priority>\n</url>'

    def get_html(self, soup):
        site_text = str(soup)
        site_text = site_text.replace('&lt;', '<')
        site_text = site_text.replace('&gt;', '>')
        return site_text

    @staticmethod
    def get_questions_script(site_data):
        with open('question_script_template.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        data['mainEntity'][0]['name'] = site_data[7]
        data['mainEntity'][0]['acceptedAnswer']['text'] = site_data[8]
        data['mainEntity'][1]['name'] = site_data[9]
        data['mainEntity'][1]['acceptedAnswer']['text'] = site_data[10]
        data['mainEntity'][2]['name'] = site_data[11]
        data['mainEntity'][2]['acceptedAnswer']['text'] = site_data[12]

        return str(json.dumps(data, ensure_ascii=False))

    @staticmethod
    def get_end_script(container_name, url):
        with open('end_script_template.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Gen random price
        min_price = random.randint(6, 8) * 100 + random.randint(0, 1) * 50
        if min_price > 800:
            min_price = 800
        max_price = random.randint(12, 15) * 100 + random.randint(0, 1) * 50
        if max_price > 1500:
            max_price = 1500
        random_price = 'от ' + str(min_price) + ' до ' + str(max_price) + ' ₽'

        data['name'] = container_name
        data['url'] = url
        data['priceRange'] = random_price
        data['aggregateRating']['reviewCount'] = str(random.randint(400, 2500))
        data['aggregateRating']['ratingValue'] = str(random.randint(47, 50) / 10)

        return str(json.dumps(data, ensure_ascii=False))

    def gen_master_item(self, master, review, num):
        # Get author data
        masters = self.master_data_df[self.master_data_df['path'] == master].values
        master_data = masters[0]

        # Get template of master item
        with open('master_item.html', 'r', encoding='utf-8') as f:
            master_item_text = f.read()

        # Filling template
        # Info
        master_item = BeautifulSoup(master_item_text, "html.parser")
        avatar_src = 'master/' + master_data[2]
        if avatar_src.split('.')[-1] != 'svg':
            avatar_src += '.jpg'
        master_item.find('div', {'data-mark': 'MasterData.logoPath'}).find('img').attrs['src'] = avatar_src
        master_item.find('h4', {'data-mark': 'MasterData.initials'}).string.replace_with(master_data[1])
        master_item.find('div', {'data-mark': 'MasterData.rate'}).find('span').string.replace_with(master_data[3])
        master_item.find('span', {'data-mark': 'MasterData.amount_reviews'})\
            .string.replace_with('Отзывы: ' + master_data[4])
        master_item.find('div', {'data-mark': 'MasterData.amount_lessons'}) \
            .string.replace_with('Уроки: ' + master_data[5])

        # Reviews
        master_item.find('p', {'data-mark': 'ReviewData.review'}).string.replace_with(review)
        reviewers_name = RussianNames().get_person().split(' ')[0]
        master_item.find('div', {'data-mark': 'ReviewData.review_customerName_date'})\
            .string = '{0} <span>{1}</span>'.format(reviewers_name, self.gen_rand_review_date())

        # About
        master_about = self.master_about_df[self.master_about_df['masterDataId'] == master].sort_values(['id'])\
            ['aboutText'].values

        about_block = master_item.find('div', {'data-mark': 'MasterAbout.aboutText'}).parent
        about_block.div.p.decompose()
        if len(master_about) > 0:
            for i in range(len(master_about)):
                new_tag = master_item.new_tag('p')
                about_block.div.insert(i, new_tag)
                about_block.find_all('p')[-1].attrs['class'] = 'hide-item'
                about_block.find_all('p')[-1].string = master_about[i]
        else:
            about_block.decompose()

        # Education
        master_education = self.master_education_df[self.master_education_df['masterDataId'] == master]\
            ['education'].values

        education_block = master_item.find('div', {'data-mark': 'MasterEducation.education'}).parent
        education_block.div.p.decompose()
        if len(master_education) > 0:
            for i in range(len(master_education)):
                new_tag = master_item.new_tag('p')
                education_block.div.insert(i, new_tag)
                education_block.find_all('p')[-1].attrs['class'] = 'hide-item'
                education_block.find_all('p')[-1].string = master_education[i]
        else:
            education_block.decompose()

        # Price, work_online, consultation
        time_spacing = [45, 60]
        master_item.find('div', {'data-mark': 'MasterData.cost_time'})\
            .string = "<span>" + master_data[6] + " ₽</span> / " + \
                      str(time_spacing[random.randint(0, len(time_spacing) - 1)]) + " мин"
        if not master_data[7]:
            master_item.find('div', {'data-mark': 'MasterData.work_online'}).decompose()
        if not master_data[8]:
            master_item.find('div', {'data-mark': 'MasterData.consultation'}).decompose()

        # Characteristic
        characteristic_block = master_item.find('div', {'data-mark': 'MasterData.characteristic'}).ul
        characteristic_block.li.decompose()

        if master_data[9]:
            new_tag = master_item.new_tag('li')
            characteristic_block.append(new_tag)
            characteristic_block.find_all('li')[-1].string = 'Дошкольники'

        if master_data[10]:
            new_tag = master_item.new_tag('li')
            characteristic_block.append(new_tag)
            characteristic_block.find_all('li')[-1].string = 'Начальные классы'

        if master_data[11]:
            new_tag = master_item.new_tag('li')
            characteristic_block.append(new_tag)
            characteristic_block.find_all('li')[-1].string = '5-9 классы'

        if master_data[12]:
            new_tag = master_item.new_tag('li')
            characteristic_block.append(new_tag)
            characteristic_block.find_all('li')[-1].string = '10-11 классы'

        if master_data[13]:
            new_tag = master_item.new_tag('li')
            characteristic_block.append(new_tag)
            characteristic_block.find_all('li')[-1].string = 'Студенты'

        if master_data[14]:
            new_tag = master_item.new_tag('li')
            characteristic_block.append(new_tag)
            characteristic_block.find_all('li')[-1].string = 'Взрослые'

        # Paste nums
        master_item.find('div', {'class': 'master__left _master-1'})['class'] = 'master__left _master-' + str(num + 1)
        master_item.find('div', {'class': 'spollers _spollers-1'})['class'] = 'spollers _spollers-'+str(num+1)
        master_item.find('div', {'data-da': '_master-1,1,991'})['data-da'] = '_master-'+str(num+1)+',1,991'
        master_item.find('div', {'data-da': '_spollers-1,2,991'})['data-da'] = '_spollers-'+str(num+1)+',2,991'

        return self.get_html(master_item)

    # Return random post date
    @staticmethod
    def gen_rand_review_date():
        dates = (
            'сегодня',
            'вчера',
            '2 дня назад',
            '3 дня назад',
            '4 дня назад',
            '5 дней назад',
            '6 дней назад',
            '7 дней назад',
            '10 дней назад',
            '20 дней назад',
            'больше месяца назад'
        )
        return dates[random.randint(0, len(dates)-1)]


