import sqlite3
from datetime import datetime
from sqlite3 import Error
import pandas as pd
from src.pricer import read_price_df

DB_FILE_PATH = 'db.sqlite'


def connect_to_db(db_file):
    """
    Connect to an SQlite database, if db file does not exist it will be created
    :param db_file: absolute or relative path of db file
    :return: sqlite3 connection
    """
    sqlite3_conn = None

    try:
        sqlite3_conn = sqlite3.connect(db_file)
        return sqlite3_conn

    except Error as err:
        print(err)

        if sqlite3_conn is not None:
            sqlite3_conn.close()


def insert_df_to_table(data: pd.DataFrame, table_name: str):
    """
    Open a csv file with pandas, store its content in a pandas data frame, change the data frame headers to the table
    column names and insert the data to the table
    :param data: Data in DataFrame format, to be populated to SQL table
    :param table_name: table name in the database to insert the data into
    :return: None
    """

    conn = connect_to_db(DB_FILE_PATH)

    if conn is not None:
        c = conn.cursor()

        # Create table if it is not exist
        c.execute('CREATE TABLE IF NOT EXISTS ' + table_name +
                  '(time    VARCHAR NOT NULL PRIMARY KEY,'
                  'open     DECIMAL,'
                  'high     DECIMAL,'
                  'low      DECIMAL,'
                  'close    DECIMAL)')

        data.columns = get_column_names_from_db_table(c, table_name)

        data.to_sql(name=table_name, con=conn, if_exists='append', index=False)

        conn.close()
        print('SQL insert process finished')
    else:
        print('Connection to database failed')


def read_price(start_date: datetime, end_date: datetime, instrument: str = 'GBP_USD') -> pd.DataFrame:
    price_df = read_price_df(instrument=instrument, granularity='S5', start=start_date, end=end_date, max_count=4000)
    price_df.reset_index(level=0, inplace=True)
    price_df['time'] = price_df['time'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'))
    return price_df


def get_column_names_from_db_table(sql_cursor, table_name):
    """
    Scrape the column names from a database table to a list
    :param sql_cursor: sqlite cursor
    :param table_name: table name to get the column names from
    :return: a list with table column names
    """

    table_column_names = 'PRAGMA table_info(' + table_name + ');'
    sql_cursor.execute(table_column_names)
    table_column_names = sql_cursor.fetchall()

    column_names = list()

    for name in table_column_names:
        column_names.append(name[1])

    return column_names


if __name__ == '__main__':
    ccy_pair = 'EUR_GBP'
    start = datetime(2015, 1, 1, 0, 0, 0)
    to = datetime(2020, 7, 31, 23, 59, 59)

    df = read_price(start_date=start, end_date=to, instrument=ccy_pair)
    # pattern: currency_pair _ ohlc
    insert_df_to_table(data=df, table_name=f"{ccy_pair.lower().replace('_', '')}_ohlc")
