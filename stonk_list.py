import random
import sqlite3
from contextlib import contextmanager
from typing import Generator, List, Tuple, Optional
from dataclasses import dataclass, asdict
import logging
import os

# Constants
DB_FILE_PATH = os.getenv('DB_FILE_PATH', 'sqlite/stonks.db')
EXCHANGE_FILES_DIRECTORY = os.getenv('EXCHANGE_FILES_DIRECTORY', 'Stonks Files/Input/')

@dataclass
class Stonk:
    symbol: str
    current: float
    pe: float
    dcf: float
    roe: float
    exchange: str
    quality: str
    title: str
    industry: str
    market_cap: float
    revenue: float
    net_income: float
    assets: float
    liabilities: float
    debt: float
    esg_score: float
    controversy: float
    summary: str
    last_updated: str

@contextmanager
def connect_to_database(db_file: str) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite database connection."""
    conn = sqlite3.connect(db_file)
    try:
        yield conn
    finally:
        conn.close()

def execute_query(query: str, params: Tuple, db_file_path: str) -> Optional[List[Tuple]]:
    """Execute a query and return the results if any."""
    try:
        with connect_to_database(db_file_path) as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Database query failed: {e}")
        return None

def update_stonk(symbol: str, stonk: Stonk, db_file_path: str) -> bool:
    """Update or insert stonk in the database."""
    stonk_data = asdict(stonk)
    values = tuple(stonk_data.values()) + (symbol,)
    try:
        with connect_to_database(db_file_path) as conn:
            cur = conn.cursor()
            if cur.execute("SELECT 1 FROM stonks WHERE symbol=?", (symbol,)).fetchone():
                cur.execute('''UPDATE stonks SET 
                    current=?, pe=?, dcf=?, roe=?, exchange=?, quality=?, title=?, 
                    industry=?, market_cap=?, revenue=?, net_income=?, assets=?, 
                    liabilities=?, debt=?, esg_score=?, controversy=?, summary=?, 
                    last_updated=? WHERE symbol=?''', values)
            else:
                cur.execute('''INSERT INTO stonks(
                    current, pe, dcf, roe, exchange, quality, title, industry, 
                    market_cap, revenue, net_income, assets, liabilities, debt, 
                    esg_score, controversy, summary, last_updated, symbol) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', values)
            conn.commit()
            return True
    except sqlite3.Error as e:
        logging.error(f"Database update failed: {e}")
        return False

def get_good_symbols(db_file_path: str, quality: str = "okay") -> List[str]:
    """Get good symbols from the database based on quality."""
    query = "SELECT symbol, quality FROM stonks"
    try:
        results = execute_query(query, (), db_file_path)
        if results:
            return [row[0] for row in results if (quality == "okay" and row[1] != "Bad") or (quality == "Good" and row[1] == "Good")]
        return []
    except Exception as e:
        logging.error(f"Error fetching symbols: {e}")
        return []

def read_symbols_from_files(file_paths: List[str]) -> List[str]:
    """Read symbols from exchange files."""
    symbols = []
    for file_path in file_paths:
        full_path = os.path.join(EXCHANGE_FILES_DIRECTORY, file_path)
        with open(full_path, "r") as file:
            symbols.extend([line.strip() for line in file if line.strip()])
    return symbols

def get_symbols(local_exchange_list: List[str], rand_value: int = 0, return_bad: bool = False) -> List[str]:
    """Get the symbols from the exchange files and add them to the database."""
    try:
        old_removed_symbols = [row[0] for row in execute_query("SELECT symbol FROM stonks WHERE quality='Bad'", (), DB_FILE_PATH) or []]
        all_symbols = read_symbols_from_files(local_exchange_list)

        with connect_to_database(DB_FILE_PATH) as conn:
            cur = conn.cursor()
            for symbol in all_symbols:
                cur.execute('''INSERT OR IGNORE INTO symbols(symbol) VALUES(?)''', (symbol,))

        symbols = [row[0] for row in execute_query("SELECT symbol FROM symbols", (), DB_FILE_PATH) or []]
        if return_bad:
            return symbols

        master_list = [symbol for symbol in symbols if symbol not in old_removed_symbols]

        if rand_value > 0:
            master_list = random.sample(master_list, min(rand_value, len(master_list)))

        logging.info(f"Master List is {len(master_list)} symbols")
        return master_list
    except Exception as e:
        logging.error(f"Error getting symbols: {e}")
        return []

