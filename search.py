import time, requests, bs4, asyncio, aiohttp, json, re
from datetime import datetime

URL = "https://www.resitalvilla.com/arama/{}/{}/{}/{}/{}/0/0/fiyat-artan/page/{}"

PINAR = """Villa Adı: {villa_name}
Giriş Tarihi: {checkin_day} {checkin_hour}
Çıkış Tarihi: {checkout_day} {checkout_hour}
Toplam Gece: {nights}
Toplam Fiyat: ₺{total}
Ön Ödeme: ₺{pre}
Kapıda Ödeme: ₺{door}
Villa Linki: {villa_url}
"""

GULCAN = """Villa Adı: {villa_name}
Giriş Tarihi: {checkin_day} {checkin_hour}
Çıkış Tarihi: {checkout_day} {checkout_hour}
Toplam Gece: {nights}
Temizlik Bedeli: ₺{cleaning}
Toplam Fiyat: ₺{total}
Ön Ödeme: ₺{pre}
Kapıda Ödeme: ₺{door}
Villa Linki: {villa_url}
"""


def get_js_vars(document: bs4.BeautifulSoup):
    tags = document.find_all('script')
    script = None
    entry_days = None
    exit_days = None
    busy_days = None
    for tag in tags:
        if 'giristarihler' in tag.text:
            script = tag
            break
    
    # giris tarihler için regex patterni
    pattern_giristarihler = r'var giristarihler = (\[.*?\]);'
    matches_giristarihler = re.search(pattern_giristarihler, script.text, re.DOTALL)

    if matches_giristarihler:
        giristarihler_str = matches_giristarihler.group(1)
        entry_days = json.loads(giristarihler_str)  # JSON stringi Python listesine dönüştürme

    # cikis tarihler için regex patterni
    pattern_cikistarihler = r'var cikistarihler = (\[.*?\]);'
    matches_cikistarihler = re.search(pattern_cikistarihler, script.text, re.DOTALL)

    if matches_cikistarihler:
        cikistarihler_str = matches_cikistarihler.group(1)
        exit_days = json.loads(cikistarihler_str)  # JSON stringi Python listesine dönüştürme
        
    return entry_days, exit_days


def is_valid_date_range(villa_adi, start_date, end_date, entry_days, exit_days, nights_before, nights_after):
    date_format = "%Y-%m-%d"
    
    # Convert string dates to datetime objects
    start_date_obj = datetime.strptime(start_date, date_format)
    end_date_obj = datetime.strptime(end_date, date_format)
    
    # Convert entry, exit, and busy days to sets of datetime objects
    entry_days_set = {datetime.strptime(day, date_format) for day in entry_days}
    exit_days_set = {datetime.strptime(day, date_format) for day in exit_days}
    
    # Early return: if the date range exactly matches an exit and entry day
    if start_date_obj in exit_days_set and end_date_obj in entry_days_set:
        return True
    
    # Find the latest exit day before the start_date
    latest_exit = max((day for day in exit_days_set if day < start_date_obj), default=None)
    
    # Find the earliest entry day after the end_date
    earliest_entry = min((day for day in entry_days_set if day > end_date_obj), default=None)
    
    # Calculate free nights before the start_date
    if latest_exit:
        free_nights_before = (start_date_obj - latest_exit).days
    else:
        free_nights_before = float('inf')
    
    # Calculate free nights after the end_date
    if earliest_entry:
        free_nights_after = (earliest_entry - end_date_obj).days
    else:
        free_nights_after = float('inf')
    
    # Check if free nights before and after meet the requirements
    result = free_nights_before >= nights_before and free_nights_after >= nights_after
    return result


# Asynchronous function to fetch HTML from a URL
async def fetch(session: aiohttp.ClientSession, url: str):
    async with session.get(url) as response:
        return await response.text()


# Asynchronous function to get villa info
async def get_villa_info(url: str):
    try:
        async with aiohttp.ClientSession() as session:
            # First request
            print(f"Resuest SENT: {url}")
            response = await fetch(session, url)
            doc = bs4.BeautifulSoup(response, 'html.parser')
            
            url_parts = url.split("/")
            checkin_day, checkout_day, name = url_parts[6].split("_")[0], url_parts[6].split("_")[1], url_parts[4]
            villa_name = doc.find(attrs={"class":"text-26 fw-400"}).text.split(">")[0]
            entry_days, exit_days = get_js_vars(doc)
            
            if not is_valid_date_range(villa_name, checkin_day, checkout_day, entry_days, exit_days, nights_before, nights_after):
                return {}
            
            # Second request 
            price_url_format = f"https://www.resitalvilla.com/kiralik-villalar/fiyathesapla/{checkin_day}/{checkout_day}/{name}/0/0/0"
            price_url = price_url_format.format(checkin_day, checkout_day, name)
            response = await fetch(session, price_url)
            response = json.loads(response)

            # Combine and return the scraped info
            checkin_hour = "16:00"
            checkout_hour = "10:00"
            nights = response["gece"]
            night_rule = int(response["mingece"])
            cleaning = response["extratemizlik"]
            total = response["fiyat"]
            pre = int(response["on_odeme"])
            door = str(int(total) - int(pre))
                
            villa_url = "/".join(url.split("/")[:-2])
            print(f"Request RESPONDED: {url}")
            
            if int(nights) < night_rule:
                info = GULCAN.format(
                    villa_name=villa_name,
                    checkin_day=checkin_day,
                    checkin_hour=checkin_hour,
                    checkout_day=checkout_day,
                    checkout_hour=checkout_hour,
                    nights=nights,
                    cleaning=cleaning,
                    total=total,
                    pre=pre,
                    door=door,
                    villa_url=villa_url
                )
            else:
                info = PINAR.format(
                    villa_name=villa_name,
                    checkin_day=checkin_day,
                    checkin_hour=checkin_hour,
                    checkout_day=checkout_day,
                    checkout_hour=checkout_hour,
                    nights=nights,
                    total=total,
                    pre=pre,
                    door=door,
                    villa_url=villa_url
                )
                
            return {"villa-name": villa_name, "villa-info": info}
    except Exception as e:
        print(f"Error getting villa info: {e}")
        return {}
     
        
async def process_villa_links(villa_links: list[str]):
    tasks = []
    for villa_link in villa_links:
        task = asyncio.create_task(get_villa_info(villa_link))
        tasks.append(task)
            
    # Gather all tasks concurrently
    return await asyncio.gather(*tasks)


# Asynchronous function to get page content
async def get_villa_links_in_page(session: aiohttp.ClientSession, page_url: str):
    try:
        response = await fetch(session, page_url)
        doc = bs4.BeautifulSoup(response, "html.parser")
        
        villa_links_in_this_page = []
        for villa_content_card in doc.find_all("div", "rentalCard__content m-10"):     
            villa_link = villa_content_card.find("a")["href"]
            villa_links_in_this_page.append(villa_link)

        print(f"Fetched {len(villa_links_in_this_page)} links in this PAGE.")
        return villa_links_in_this_page

    except Exception as e:
        print(f"Error fetching page: {e}")
        return []


async def process_page_nums(page_nums: list, search_params: tuple):
    async with aiohttp.ClientSession() as session:
        tasks = []  
        for page_num in page_nums:
            page_url = get_search_url(*search_params, page_num)
            task = asyncio.create_task(get_villa_links_in_page(session, page_url))
            tasks.append(task)
        
        # Gather all tasks concurrently
        villa_links = list()
        villa_links_wrapper = await asyncio.gather(*tasks)
        [villa_links.extend(inner) for inner in villa_links_wrapper]
        return villa_links


def get_search_url(date_range, features, area, parent, child, page):
    return URL.format(date_range, "-".join(features), area, parent, child, page)


    global nights_after
    global nights_before
    ranges_in_range, parent_range_start, parent_range_end, range_lenghts, holiday_ranges, nights_before, nights_after, parent, child, features, areas = parameters.values()
    # TODO - implement RANGES-IN-RANGE SEARCHING conditions
    all_villas = list()

    for holiday_range in holiday_ranges:
        for area in areas:
            url = get_search_url(holiday_range, features, area, parent, child, 1)
            print(url)
            
            pre_request_result = requests.get(url)
            doc = bs4.BeautifulSoup(pre_request_result.text, "html.parser")
            nav_button = doc.find("div", "row x-gap-20 y-gap-20 items-center justify-center")
            if nav_button is None:
                page_count = 1
            else:
                page_count = int(nav_button.find_all("a")[-1].text.split(">")[0])

            # Iterate through each page for this search conditions
            page_nums = list(range(1, page_count+1))
            print(f'{page_count} pages has found.\n')
            search_params = (holiday_range, features, area, parent, child)

            villa_links = asyncio.run(process_page_nums(page_nums, search_params))
            print(f'\n{len(villa_links)} links fetched in TOTAL.')
            
            villa_dicts = asyncio.run(process_villa_links(villa_links))
            while {} in villa_dicts:
                villa_dicts.remove({})
            print(f'Got {len(villa_dicts)} suitable villas. {len(villa_links) - len(villa_dicts)} of them are invalid')

            all_villas.extend(villa_dicts)

    return all_villas
                
                
if __name__ == "__main__":
    parameters1 = {
    'ranges-in-range': bool(),
    'parent-range-start': str(),
    'parent-range-end': str(),
    'child-range-lenghts': list[int],
    'holiday-ranges': ['2024-09-1_2024-09-4'],
    'nights-nefore': 3,
    'night-after': 3,
    'parent': '11',
    'child': '0',
    'features': ["179"],
    'areas': ["0"],
    }

    if not ranges_in_range:
        # Search for villas in a generic
        holiday_start = ' '
        while holiday_start:    
            holiday_start = input('Holiday start(yy-mm-dd): ')
            if not holiday_start:
                break
            holiday_end = input('Holiday end(yy-mm-dd): ')
            holiday_range = holiday_start + '_' + holiday_end
            holiday_ranges.append(holiday_range)
            
    else:
        # Search for multiple ranges in a estimatted holiday length
        parent_range_start = input('Range start(yy-mm-dd): ')
        # TODO
        
    start = time.time()
    
    villas = search_villas(parameters1)
    for villa in villas:
        print(villa['villa-info'], '\n')
    print("Tamamlanma süresi: %.4f" % (time.time() - start))
