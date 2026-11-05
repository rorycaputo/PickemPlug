from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import base64

def get_pickem_html(u, p):
    print('Starting Selenium Driver to fetch Pickem spreads...')
    driver = webdriver.Firefox()
    try:
        driver.get("https://picks.cbssports.com/football/pickem/pools/kbxw63b2geztqnjuha2ds/join?device=desktop%2Cdesktop&poolId=kbxw63b2geztqnjuha2ds&returnUrl=https%3A%2F%2Fpicks.cbssports.com%2Ffootball%2Fpickem%2Fpools%2Fkbxw63b2geztqnjuha2ds%3Fdevice%3Ddesktop%26device%3Ddesktop")

        login_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Log In')]")
        login_button.click()

        wait = WebDriverWait(driver, 10)
        username_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@name='email']")))
        username_input.send_keys(u)

        pass_input = driver.find_element(By.XPATH, "//input[@name='password']")
        try:
            pass_input.send_keys(base64.b64decode(p).decode('utf-8'))
        except Exception as err:
            print(f'Base64 decoding of password failed. Did you enter it?')
            raise err

        continue_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        continue_button.click()

        wait = WebDriverWait(driver, 20)
        username_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@data-cy='spread']")))
        pickem_html = driver.page_source
       
        driver.quit()
        print('Selenium Driver succeeded')
        return pickem_html
    except Exception as err:
        driver.quit()
        print(f'Selenium Driver failed: {err}')
        return None