import logging
import random
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger: logging.Logger = logging.getLogger(__name__)
ROLE = "Data Scientist"
LOCATION = "Toronto, ON"
BASE_URL = "https://www.glassdoor.ca"  # Glassdoor base URL

# List of User-Agents (expanded)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/118.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/118.0.2088.46',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
]

# List of Proxies (replace with your actual proxies)
PROXIES = [
    # Example format: 'http://user:pass@ip:port' or 'http://ip:port'
    'http://user:pass@103.163.10.10:8080',
    'http://user:pass@103.163.10.11:8080',
    'http://user:pass@103.163.10.12:8080',
    'http://user:pass@103.163.10.13:8080',
    'http://user:pass@103.163.10.14:8080',
    'http://user:pass@103.163.10.15:8080',
    'http://user:pass@103.163.10.16:8080',
    'http://user:pass@103.163.10.17:8080',
    'http://user:pass@103.163.10.18:8080',
    'http://user:pass@103.163.10.19:8080',
]


def get_random_user_agent():
    return random.choice(USER_AGENTS)


def get_random_proxy():
    return random.choice(PROXIES)


def simulate_human_behavior(driver):
    """Simulates human-like behavior on the page."""
    # Scroll down the page a bit
    scroll_amount = random.randint(200, 500)
    driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
    time.sleep(random.uniform(0.5, 1.5))

    # Move the mouse randomly
    actions = ActionChains(driver)
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        actions.move_to_element_with_offset(body, random.randint(0, 500), random.randint(0, 500)).perform()
        time.sleep(random.uniform(0.5, 1.5))
    except NoSuchElementException:
        logger.warning("Could not find body element for mouse movement.")

    # Maybe click on a random element (optional)
    if random.random() < 0.3:  # 30% chance of clicking
        try:
            all_links = driver.find_elements(By.TAG_NAME, "a")
            if all_links:
                random_link = random.choice(all_links)
                actions.move_to_element(random_link).click().perform()
                time.sleep(random.uniform(1, 3))
                driver.back()
        except NoSuchElementException:
            logger.warning("Could not find any links to click.")
        except Exception as e:
            logger.error(f"Error clicking on a random link: {str(e)}")


def test_glassdoor_scraper_selenium() -> None:
    jobs = []
    start = 0
    has_more = True

    # Set up Selenium with Chrome (you'll need to download ChromeDriver)
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-agent={get_random_user_agent()}")
    # options.add_argument("--headless")  # Remove headless mode

    # Set up proxy
    proxy = get_random_proxy()
    options.add_argument(f"--proxy-server={proxy}")
    logger.info(f"Using proxy: {proxy}")

    driver = webdriver.Chrome(options=options)

    try:
        while has_more:
            search_url = f"{BASE_URL}/Job/jobs.htm?sc.keyword={ROLE}&locT=C&locId=15&locKeyword={LOCATION}&jobType=all&fromAge=-1&minSalary=0&maxSalary=0&radius=0&cityId=-1&pageSize=30&firstJob=0&start={start}"
            logger.info(f"Navigating to: {search_url}")
            driver.get(search_url)

            # Simulate human behavior
            simulate_human_behavior(driver)

            # Wait for the job cards to load (adjust the timeout as needed)
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "jobCard"))
                )
            except TimeoutException:
                logger.warning("Timeout waiting for job cards to load.")
                break

            # Get the page source after JavaScript has executed
            soup = BeautifulSoup(driver.page_source, "html.parser")

            job_cards = soup.find_all("li", class_="jobCard")

            if not job_cards:
                logger.warning("Could not find job cards in response. Stopping.")
                break

            for card in job_cards:
                try:
                    title_element = card.find("a", class_="jobLink")
                    title = title_element.text.strip() if title_element else ""

                    company_element = card.find("a", class_="jobCard_companyName")
                    company = company_element.text.strip() if company_element else ""

                    location_element = card.find("div", class_="jobCard_location")
                    location = location_element.text.strip() if location_element else ""

                    description_element = card.find("div", class_="jobCard_jobDescription")
                    description = description_element.text.strip() if description_element else ""

                    job_link_element = card.find("a", class_="jobLink")
                    job_url = BASE_URL + job_link_element["href"] if job_link_element and "href" in job_link_element.attrs else ""

                    jobs.append({
                        'title': title,
                        'company': company,
                        'location': location,
                        'description': description,
                        'source_url': job_url,
                        'source': 'glassdoor',
                        'posted_date': ""  # You'll need to find the date element in the HTML
                    })
                except Exception as e:
                    logger.error(f"Error parsing job card: {str(e)}")
                    continue

            # Basic pagination check (you'll need to improve this)
            if start > 100:
                has_more = False
            else:
                start += 30

            # Add random delay
            delay = random.uniform(5, 10)  # Delay between 5 and 10 seconds
            logger.info(f"Waiting for {delay:.2f} seconds...")
            time.sleep(delay)

    except WebDriverException as e:
        logger.error(f"WebDriver error: {e}")
        if "ERR_PROXY_CONNECTION_FAILED" in str(e):
            logger.error("Proxy connection failed. Check your proxy settings.")
    except Exception as e:
        logger.error(f"Error in test_glassdoor_scraper_selenium: {str(e)}")
        raise
    finally:
        driver.quit()  # Close the browser

    # Print the jobs found
    for job in jobs:
        print(job)


test_glassdoor_scraper_selenium()
