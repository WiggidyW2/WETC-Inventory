import db
import esi

import sqlite3

import gspread

SHEETS_SERVICE_KEY_PATH = "wetc-inventory-key.json"
TYPE_INFO_CSV_PATH = "type_info.csv"

INVENTORY_SHEET = "Inventory"
CONFIG_SHEET = "InventoryConfig"

LOCATIONS_WS = "Locations"
CATEGORIES_WS = "TradingGroups"
TYPE_IDS_WS = "TypeIDs"
GROUP_IDS_WS = "GroupIDs"
CATEGORY_ID_WS = "CategoryIDs"
ESI_CONFIG_WS = "ESIConfig"
MARKET_WS = "Markets"

OFFICE_TYPE_ID = 27
CONTAINER_IDS = [
	17366, # Station Container
	17367, # Station Vault Container
	17368, # Station Warehouse Container
	3297, # Small Standard Container
	3293, # Medium Standard Container
	3296, # Large Standard Container
	3467, # Small Secure Container
	3466, # Medium Secure Container
	3465, # Large Secure Container
	11488, # Huge Secure Container
	11489, # Giant Secure Container
	33011, # Small Freight Container
	33009, # Medium Freight Container
	33007, # Large Freight Container
	33005, # Huge Freight Container
	24445, # Giant Freight Container
	33003, # Enormous Freight Container
	17363, # Small Audit Log Secure Container
	17364, # Medium Audit Log Secure Container
	17365 # Large Audit Log Secure Container
]
HANGARS = {
	1: "CorpSAG1",
	2: "CorpSAG2",
	3: "CorpSAG3",
	4: "CorpSAG4",
	5: "CorpSAG5",
	6: "CorpSAG6",
	7: "CorpSAG7"
}
CONTAINER_FLAGS = [
	"Unlocked",
	"Locked"
]

FAILURE = False
SUCCESS = True

TYPE_INFO_DB = db.TypeInfoDB(TYPE_INFO_CSV_PATH)
PRICES_DB = db.PricesDB()

class Item:
	def __init__(self, raw_item):
		self.item_id = raw_item['item_id']
		self.location_flag = raw_item['location_flag']
		self.location_id = raw_item['location_id']
		self.quantity = raw_item['quantity']
		self.type_id = raw_item['type_id']
		self.group_id = None
		self.category_id = None
		self._type_name = None

	def set_ids(self):
		if not self.has_ids():
			self.set_type_info()

	def has_ids(self):
		if self.group_id is not None and self.category_id is not None:
			return True
		else:
			return False

	def type_name(self):
		if self._type_name:
			return self._type_name
		else:
			self.set_type_info()
			return self._type_name

	def price(self, price_market, price_kind, price_multiplier):
		cursor = PRICES_DB.cursor()
		base_price = 0.0
		if price_kind == 'Buy':
			base_price = parse_db_price(PRICES_DB.get_max_buy(cursor, self.type_id, price_market).fetchone())
		elif price_kind == 'Sell':
			base_price = parse_db_price(PRICES_DB.get_min_sell(cursor, self.type_id, price_market).fetchone())
		elif price_kind == 'Split':
			buy_price = parse_db_price(PRICES_DB.get_max_buy(cursor, self.type_id, price_market).fetchone())
			sell_price = parse_db_price(PRICES_DB.get_min_sell(cursor, self.type_id, price_market).fetchone())
			if buy_price == 0.0:
				buy_price = sell_price
			if sell_price == 0.0:
				sell_price = buy_price
			base_price = (buy_price + sell_price) / 2
		else:
			raise Exception("Invalid Price Kind: {}".format(price_kind))
		price = base_price * price_multiplier
		return price

	def set_type_info(self):
		cur = TYPE_INFO_DB.cursor()
		type_info = TYPE_INFO_DB.get_type_info(cur, self.type_id).fetchone()
		self._type_name = type_info[0]
		self.group_id = type_info[1]
		self.category_id = type_info[2]

class Category:
	def __init__(self, name, price_market, price_kind, price_multiplier, type_ids, group_ids, category_ids):
		self.name = name
		self.price_market = price_market
		self.price_kind = price_kind
		self.price_multiplier = price_multiplier
		self.items = {}
		self.type_ids = type_ids
		self.group_ids = group_ids
		self.category_ids = category_ids

	def add_type_id(self, type_id):
		self.type_ids.append(type_id)

	def add_group_id(self, group_id):
		self.type_ids.append(group_id)

	def add_category_id(self, category_id):
		self.type_ids.append(category_id)

	def try_add_by_type_id(self, item):
		if item.type_id in self.type_ids:
			self.add(item)
			return SUCCESS
		else:
			return FAILURE

	def try_add_by_group_id(self, item):
		if item.group_id in self.group_ids:
			self.add(item)
			return SUCCESS
		else:
			return FAILURE

	def try_add_by_category_id(self, item):
		if item.category_id in self.category_ids:
			self.add(item)
			return SUCCESS
		else:
			return FAILURE

	def add(self, item):
		if item.type_id in self.items:
			self.items[item.type_id].quantity += item.quantity
		else:
			self.items.update({item.type_id: item})

class Location:
	def __init__(self, name, location_id, enabled_flags):
		self.name = name
		self.location_id = location_id
		self.enabled_flags = enabled_flags
		self.categories = []

	def add_category(self, category):
		self.categories.append(category)

	def try_add(self, item):
		if item.location_id == self.location_id:
			if item.location_flag in self.enabled_flags:
				for category in self.categories:
					result = category.try_add_by_type_id(item)
					if result == SUCCESS:
						return SUCCESS
				item.set_ids()
				for category in self.categories:
					result = category.try_add_by_group_id(item)
					if result == SUCCESS:
						return SUCCESS
				for category in self.categories:
					result = category.try_add_by_category_id(item)
					if result == SUCCESS:
						return SUCCESS
		return FAILURE

def parse_db_price(price):
	if price is None:
		return 0.0
	else:
		return price[0]

def parse_raw_items(raw_items):
	items = []
	containers = {}
	offices = {}
	for raw_item in raw_items:
		item = Item(raw_item)
		if item.type_id in CONTAINER_IDS:
			containers.update({item.item_id: item})
		elif item.type_id == OFFICE_TYPE_ID:
			offices.update({item.item_id: item})
		else:
			items.append(item)
	return items, containers, offices

def flatten_location(item, containers, offices):
	if item.location_flag in CONTAINER_FLAGS:
		container = containers[item.location_id]
		item.location_flag = container.location_flag
		item.location_id = container.location_id
	if item.location_id in offices:
		item.location_id = offices[item.location_id].location_id

def insert_items(items, containers, offices, locations):
	for item in items:
		flatten_location(item, containers, offices)
		for location in locations:
			result = location.try_add(item)
			if result == SUCCESS:
				break

def get_esi_config(sheet):
	worksheet = sheet.worksheet(ESI_CONFIG_WS)
	entries = worksheet.col_values(2)
	client_id = entries[0]
	secret_key = entries[1]
	callback_url = entries[2]
	user_agent = entries[3]
	refresh_token = entries[4]
	corporation_id = entries[5]
	return (client_id, secret_key, callback_url, user_agent, refresh_token, corporation_id)

def get_locations(sheet):
	locations = []
	worksheet = sheet.worksheet(LOCATIONS_WS)
	rows = worksheet.get_all_values()
	
	if len(rows) > 1:
		for row in rows[1:]:
			name = str(row[0])
			location_id = int(row[1])

			hangar_flags = []
			flag_i = 1
			for hangar_i in range(2, 9):
				if row[hangar_i] == "TRUE":
					hangar_flags.append(HANGARS[flag_i])
				flag_i += 1

			location = Location(name, location_id, hangar_flags)
			locations.append(location)

	return locations

def get_idents(sheet, worksheet_name):
	idents = {}
	worksheet = sheet.worksheet(worksheet_name)
	rows = worksheet.get_all_values()
	
	if len(rows) > 1:
		for row in rows[1:]:
			category_name = str(row[0])
			ident = int(row[1])
			if category_name in idents:
				idents[category_name].append(ident)
			else:
				idents.update({category_name: [ident]})

	return idents

def get_markets(sheet, worksheet_name):
	markets = {}
	worksheet = sheet.worksheet(worksheet_name)
	rows = worksheet.get_all_values()

	if len(rows) > 1:
		for row in rows[1:]:
			market_name = str(row[0])
			structure_id = int(row[1])
			region_id = int(row[2])
			kind = str(row[3])
			markets.update({market_name: {
				'market_name': market_name,
				'structure_id': structure_id,
				'region_id': region_id,
				'kind': kind,
			}})
	
	return markets

def insert_categories(sheet, locations, type_ids, group_ids, category_ids):
	worksheet = sheet.worksheet(CATEGORIES_WS)
	rows = worksheet.get_all_values()

	if len(rows) > 1:
		for row in rows[1:]:
			category_name = str(row[0])
			price_market = str(row[2])
			price_kind = str(row[3])
			price_multiplier = float(row[4])
			category_type_ids = type_ids.get(category_name, [])
			category_group_ids = group_ids.get(category_name, [])
			category_category_ids = category_ids.get(category_name, [])
			category = Category(
				category_name,
				price_market,
				price_kind,
				price_multiplier,
				category_type_ids,
				category_group_ids,
				category_category_ids,
			)
			for location in locations:
				if location.name == str(row[1]):
					location.add_category(category)
					break

def insert_into_worksheet(worksheet, data):
	worksheet.clear()
	worksheet.update('A1', data)

def update_worksheets(sheet, locations):
	for location in locations:
		for category in location.categories:
			price_string = "{}% {} {}".format(
				int(category.price_multiplier * 100),
				category.price_market,
				category.price_kind,
			)
			data = [["Name", "Quantity", "1x " + price_string, "All " + price_string]]
			for item in category.items.values():
				item_name = item.type_name()
				item_quantity = item.quantity
				item_price = item.price(category.price_market, category.price_kind, category.price_multiplier)
				all_item_price = item_price * float(item_quantity)
				data.append([item_name, item_quantity, item_price, all_item_price])
			worksheet = None
			try:
				worksheet = sheet.worksheet(category.name)
			except gspread.exceptions.WorksheetNotFound:
				worksheet = sheet.add_worksheet(title=category.name, rows=len(category.items) + 1, cols=4)
			insert_into_worksheet(worksheet, data)

def download_orders(client, region_id, location_id, kind):
	orders = None
	if kind == 'Station':
		orders = client.download_station_prices(region_id, location_id)
	elif kind == 'Structure':
		orders = client.download_structure_prices(location_id)
	else:
		raise Exception("Invalid Market Kind: {}".format(kind))
	for order in orders:
		try:
			PRICES_DB.import_order(
				int(order['order_id']),
				int(order['type_id']),
				int(bool(order['is_buy_order'])),
				float(order['price']),
				int(order['location_id']),
			)
		except sqlite3.IntegrityError:
			pass

def main():
	service = gspread.service_account(filename=SHEETS_SERVICE_KEY_PATH)
	sheet = service.open(CONFIG_SHEET)

	client_id, secret_key, callback_url, user_agent, refresh_token, corporation_id = get_esi_config(sheet)
	client = esi.Client(client_id, secret_key, callback_url, user_agent, refresh_token)

	markets = get_markets(sheet, MARKET_WS)
	PRICES_DB.set_markets(markets)
	PRICES_DB.delete_orders()
	for market in markets.values():
		download_orders(
			client,
			market['region_id'],
			market['structure_id'],
			market['kind'],
		)
	PRICES_DB.commit()

	locations = get_locations(sheet)
	type_ids = get_idents(sheet, TYPE_IDS_WS)
	group_ids = get_idents(sheet, GROUP_IDS_WS)
	category_ids = get_idents(sheet, CATEGORY_ID_WS)
	insert_categories(sheet, locations, type_ids, group_ids, category_ids)

	raw_items = client.get_corporation_assets(corporation_id)
	items, containers, offices = parse_raw_items(raw_items)
	insert_items(items, containers, offices, locations)

	sheet = service.open(INVENTORY_SHEET)
	update_worksheets(sheet, locations)

if __name__ == '__main__':
	main()
