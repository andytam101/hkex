from selenium import webdriver
from selenium.webdriver.common.by import By
import logging

import argparse
import csv


class InvalidStockException(Exception):
    def __init__(self, code, *args: object) -> None:
        super().__init__(*args)
        self.code = code


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("-o", "--output", default="output.csv")
    parser.add_argument("-s", "--stocks", default="stocks.txt")

    return parser.parse_args()


class ExtractData:
    def __init__(
            self,
            url,
            stocks_path="",
            output_path="data.csv"
        ) -> None:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        self.driver = webdriver.Chrome(options=options)

        self.url = url
        
        self.stocks = self.get_wanted_stocks(stocks_path)
        self.output_file = open(output_path, "w", newline='')
        self.writer = csv.writer(self.output_file, delimiter=',')
        
        logging.basicConfig(filename="logs.log", level=logging.INFO)

        self.currencies = {
            "HKD", "USD", "CNY", "GBP", "JPY"
        }

    def remove_commas(self, num: str):
        return num.replace(",", "")

    def get_wanted_stocks(self, stocks_path):
        with open(stocks_path, "r") as f:
            stocks = f.read().splitlines()
        
        stocks = filter(lambda x: len(x.strip()) > 0, stocks)

        return set(map(lambda x: int(x.strip()), stocks))

    def write_stock(self, stock):
        self.writer.writerow(stock)

    def read_page(self):
        self.driver.get(self.url)
        text = self.driver.find_element(By.CSS_SELECTOR, "body").text
        lines = text.splitlines()
        return lines

    def remove_top(self, lines):
        quot_count = 0
        for idx, line in enumerate(lines):
            line = line.strip()
            if line == "QUOTATIONS":
                quot_count += 1
            
            if quot_count == 2:
                break

        return idx

    def is_wanted_stock(self, line: str):
        words = line.split()
        try:
            x = int(words[0])
            return x in self.stocks
        except (ValueError, IndexError):
            # not a stock code
            return False
        
    def classify_stock(self, line: str, next_line: str):
        words  = line.split()
        code = int(words[0])

        try:
            prices = next_line.split()
            # locate currency
            for idx, word in enumerate(words):
                if word in self.currencies:
                    break
            currency = word
            name = " ".join(words[1:idx])

            if words[-2] == "TRADING" and words[-1] == "SUSPENDED":
                # TODO: handle suspended stocks
                logging.info(f"Stock number {code} is suspended.")
                prev_clos = ask = high = shares_traded = closing = bid = low = turnover = -1
            else:    
                try:
                    prev_clos = float(words[idx + 1])
                except (ValueError, IndexError):
                    logging.info(f"Stock number {code} has missing data.")
                    prev_clos = -1
                try:
                    ask = float(words[idx + 2])
                except (ValueError, IndexError):
                    logging.info(f"Stock number {code} has missing data.")
                    ask = -1
                try:
                    high = float(words[idx + 3])
                except (ValueError, IndexError):
                    logging.info(f"Stock number {code} has missing data.")
                    high = -1
                try:
                    shares_traded = int(self.remove_commas(words[idx + 4]))
                except (ValueError, IndexError):
                    logging.info(f"Stock number {code} has missing data.")
                    shares_traded = -1

                try:
                    closing  = float(prices[0])
                except (ValueError, IndexError):
                    logging.info(f"Stock number {code} has missing data.")
                    closing = -1
                try:
                    bid      = float(prices[1])
                except (ValueError, IndexError):
                    logging.info(f"Stock number {code} has missing data.")
                    bid = -1
                try:
                    low      = float(prices[2])
                except (ValueError, IndexError):
                    logging.info(f"Stock number {code} has missing data.")
                    low = -1
                try:
                    turnover = int(self.remove_commas(prices[3]))
                except (ValueError, IndexError):
                    logging.info(f"Stock number {code} has missing data.")
                    turnover = -1

            return [code, name, currency, prev_clos, closing, ask, bid, high, low, shares_traded, turnover]

        except Exception:
            raise InvalidStockException(code=code)


    def run(self):
        # write header
        header = ["code", "name", "cur", "prev clos", "closing", "ask", "bid", "high", "low", "shares traded", "turnover"]
        self.writer.writerow(header)

        print("Reading website...")
        lines = self.read_page()
        start_idx = self.remove_top(lines)
        
        print("Reading stocks...")
        lines = lines[start_idx:]
        for idx, line in enumerate(lines):
            if self.is_wanted_stock(line):
                try:
                    stock = self.classify_stock(line, lines[idx + 1])
                    self.write_stock(stock)
                    logging.info(f"Stock code {stock[0]} has been successfully written.")
                    self.stocks.remove(stock[0])
                    if len(self.stocks) == 0:
                        break
                except InvalidStockException as e:
                    self.stocks.remove(e.code)
                    logging.error(f"Stock code {e.code} could not be retrieved. Exception: Invalid stock.")


    def quit(self):
        if len(self.stocks) > 0:
            message = f"These stocks were not read: {', '.join(self.stocks)}"
            print(message)
            logging.error(message)

        self.output_file.close()
        self.driver.quit()


def main():
    args = get_args()

    extract_data = ExtractData(
        url=args.url,
        stocks_path=args.stocks,
        output_path=args.output
    )

    extract_data.run()
    extract_data.quit()

if __name__ == "__main__":
    main()
