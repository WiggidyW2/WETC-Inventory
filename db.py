import sqlite3

TYPE_INFO_DB_PATH = "TypeInfo.sqlite"
PRICES_DB_PATH = "Prices.sqlite"

class TypeInfoDB:
	def __init__(self, csv_path):
		self.con = sqlite3.connect(TYPE_INFO_DB_PATH)
		self.initialize_table()
		self.import_csv(csv_path)

	def cursor(self):
		return self.con.cursor()

	def initialize_table(self):
		cursor = self.cursor()
		cursor.execute("""
			CREATE TABLE IF NOT EXISTS TYPE_INFO (
				TYPE_ID INTEGER NOT NULL PRIMARY KEY,
				GROUP_ID INTEGER NOT NULL,
				CATEGORY_ID INTEGER NOT NULL,
				NAME TEXT
			)
		""")
		self.con.commit()

	def import_csv(self, csv_path):
		cursor = self.cursor()
		cursor.execute("""
			DELETE FROM TYPE_INFO
		""")
		with open(csv_path, 'r') as f:
			f.readline() # ignore header row
			for line in f.readlines():
				line = line.split(',', 3)
				cursor.execute("""
					INSERT INTO TYPE_INFO
					VALUES (?,?,?,?)
				""", [
					int(line[0]),
					int(line[1]),
					int(line[2]),
					line[3].replace('\n', '')
				])
		self.con.commit()

	def get_type_info(self, cur, type_id):
		return cur.execute("""
			SELECT NAME, GROUP_ID, CATEGORY_ID
			FROM TYPE_INFO
			WHERE TYPE_ID = ?
		""", [type_id])

class PricesDB:
	def __init__(self):
		self.con = sqlite3.connect(PRICES_DB_PATH)
		self.initialize_table()
		self.markets = {}

	def cursor(self):
		return self.con.cursor()

	def commit(self):
		self.con.commit()

	def set_markets(self, markets):
		self.markets = markets

	def initialize_table(self):
		cursor = self.cursor()
		cursor.execute("""
			CREATE TABLE IF NOT EXISTS ORDERS (
				ORDER_ID INTEGER NOT NULL PRIMARY KEY,
				TYPE_ID INTEGER NOT NULL,
				IS_BUY INTEGER NOT NULL,
				PRICE REAL NOT NULL,
				LOCATION_ID INTEGER NOT NULL
			)
		""")
		self.con.commit()

	def delete_orders(self):
		cursor = self.cursor()
		cursor.execute("""
			DELETE FROM ORDERS
		""")

	def import_order(self, order_id, type_id, is_buy, price, location_id):
		cursor = self.cursor()
		cursor.execute("""
			INSERT INTO ORDERS
			VALUES (?,?,?,?,?)
		""", (order_id, type_id, is_buy, price, location_id))

	def get_max_buy(self, cursor, type_id, price_market):
		location_id = self.markets[price_market]['structure_id']
		return cursor.execute("""
			SELECT PRICE
			FROM ORDERS
			WHERE
				IS_BUY = 1
				AND
				(TYPE_ID, LOCATION_ID) = (?,?)
			ORDER BY PRICE DESC
		""", (type_id, location_id))

	def get_min_sell(self, cursor, type_id, price_market):
		location_id = self.markets[price_market]['structure_id']
		return cursor.execute("""
			SELECT PRICE
			FROM ORDERS
			WHERE
				IS_BUY = 0
				AND
				(TYPE_ID, LOCATION_ID) = (?,?)
			ORDER BY PRICE ASC
		""", (type_id, location_id))