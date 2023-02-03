import esipy

SWAGGER_URL = "https://esi.evetech.net/latest/swagger.json?datasource=tranquility"

class Client:
	def __init__(self, client_id, secret_key, callback_url, user_agent, refresh_token):
		security = esipy.EsiSecurity(
			client_id=client_id,
			secret_key=secret_key,
			redirect_uri=callback_url,
			headers={'User-Agent': user_agent},
		)
		security.update_token({
			'access_token': '',
			'expires_in': -1,
			'refresh_token': refresh_token,
		})
		security.refresh()
		
		self.esi_app = esipy.App.create(url=SWAGGER_URL)
		self.esi_client = esipy.EsiClient(
			headers={'User-Agent': user_agent},
			security=security,
			retry_requests=True,
			raw_body_only=False,
		)

	def get_corporation_assets(self, corporation_id):
		op = self.esi_app.op['get_corporations_corporation_id_assets'](
			corporation_id=corporation_id,
		)
		rep = self.esi_client.head(op)
		num_pages = rep.header['X-Pages'][0]
		ops = []
		for page in range(1, num_pages + 1):
			ops.append(self.esi_app.op['get_corporations_corporation_id_assets'](
				corporation_id=corporation_id,
				page=page,
			))
		reps = self.esi_client.multi_request(ops)
		assets = []
		for rep in reps:
			for asset in rep[1].data:
				assets.append(asset)
		return assets

	def download_station_prices(self, region_id, station_id):
		op = self.esi_app.op['get_markets_region_id_orders'](
			order_type='all',
			region_id=region_id,
		)
		rep = self.esi_client.head(op)
		num_pages = rep.header['X-Pages'][0]
		ops = []
		for page in range(1, num_pages + 1):
			ops.append(self.esi_app.op['get_markets_region_id_orders'](
				order_type='all',
				region_id=region_id,
				page=page,
			))
		reps = self.esi_client.multi_request(ops)
		orders = []
		for rep in reps:
			for order in rep[1].data:
				if order['location_id'] == station_id:
					orders.append(order)
		return orders

	def download_structure_prices(self, structure_id):
		op = self.esi_app.op['get_markets_structures_structure_id'](
			structure_id=structure_id,
		)
		rep = self.esi_client.head(op)
		num_pages = rep.header['X-Pages'][0]
		ops = []
		for page in range(1, num_pages + 1):
			ops.append(self.esi_app.op['get_markets_structures_structure_id'](
				structure_id=structure_id,
				page=page,
			))
		reps = self.esi_client.multi_request(ops)
		orders = []
		for rep in reps:
			for order in rep[1].data:
				orders.append(order)
		return orders
