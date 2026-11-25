from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import traceback
import pickem

DEBUG_SCREENSHOT = 'selenium_failure.png'
STARTUP_ATTEMPTS = 2

def _start_driver():
    """Start Firefox, retrying once since cold starts after idle time can fail."""
    last_err = None
    for attempt in range(1, STARTUP_ATTEMPTS + 1):
        try:
            return webdriver.Firefox()
        except Exception as err:
            last_err = err
            print(f'Firefox startup attempt {attempt}/{STARTUP_ATTEMPTS} failed: {err}')
            time.sleep(2)
    raise last_err


def get_pickem_html(u, p):
    """Log in from the lobby, open the pool, and return (page_source, cookies), or None if any step fails."""
    print('Starting Selenium Driver to fetch Pickem spreads...')
    driver = None
    try:
        driver = _start_driver()
        driver.get(pickem.LOBBY_URL)

        wait = WebDriverWait(driver, 20)
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Log In')]")))
        login_button.click()

        username_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@name='email']")))
        username_input.send_keys(u)

        pass_input = driver.find_element(By.XPATH, "//input[@name='password']")
        pass_input.send_keys(p)

        continue_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        continue_button.click()

        # CBS redirects back to the lobby; the pool shows up in its memberships once the login has taken effect.
        pool_url = WebDriverWait(driver, 30).until(lambda d: pickem.find_pool_url(d.page_source)[0])
        driver.find_element(By.XPATH, f"//a[starts-with(@href, '{pool_url}')]").click()

        WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.XPATH, "//div[@data-cy='spread']")))
        pickem_html = driver.page_source
        cookies = driver.get_cookies()
        print('Selenium Driver succeeded')
        return pickem_html, cookies
    except Exception as err:
        print(f'Selenium Driver failed: {err}')
        print(traceback.format_exc())
        if driver is not None:
            try:
                print(f'Page URL at failure: {driver.current_url}')
                driver.save_screenshot(DEBUG_SCREENSHOT)
                print(f'Saved failure screenshot to {DEBUG_SCREENSHOT}')
            except Exception as shot_err:
                print(f'Could not capture debug info: {shot_err}')
        return None
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception as quit_err:
                print(f'driver.quit() failed: {quit_err}')
