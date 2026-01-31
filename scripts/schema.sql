CREATE TABLE users (
	id INTEGER NOT NULL, 
	full_name VARCHAR(100) NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	phone VARCHAR(15), 
	hashed_password VARCHAR(255) NOT NULL, 
	spice_preference VARCHAR(20), 
	loyalty_coins INTEGER, 
	default_address_id INTEGER, 
	is_admin BOOLEAN, 
	is_verified BOOLEAN, 
	otp_code VARCHAR(10), 
	refresh_token VARCHAR(255), 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_id ON users (id);
CREATE UNIQUE INDEX ix_users_phone ON users (phone);
CREATE TABLE menu_items (
	id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description TEXT, 
	price FLOAT NOT NULL, 
	category VARCHAR(50), 
	image_url VARCHAR(255), 
	is_available BOOLEAN, 
	stock_count INTEGER, 
	preparation_time_mins INTEGER, 
	is_bestseller BOOLEAN, 
	is_new BOOLEAN, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_menu_items_name ON menu_items (name);
CREATE INDEX ix_menu_items_id ON menu_items (id);
CREATE TABLE kitchen_status (
	id INTEGER NOT NULL, 
	is_open BOOLEAN, 
	current_load INTEGER, 
	base_eta_mins INTEGER, 
	extra_eta_mins INTEGER, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_kitchen_status_id ON kitchen_status (id);
CREATE TABLE promo_codes (
	id INTEGER NOT NULL, 
	code VARCHAR(20) NOT NULL, 
	discount_percentage INTEGER, 
	max_discount_amount FLOAT, 
	min_order_amount FLOAT, 
	expiry_date DATETIME, 
	is_active BOOLEAN, 
	usage_limit INTEGER, 
	usage_count INTEGER, 
	description VARCHAR(255), 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_promo_codes_code ON promo_codes (code);
CREATE INDEX ix_promo_codes_id ON promo_codes (id);
CREATE TABLE addresses (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	label VARCHAR(50), 
	address_text TEXT NOT NULL, 
	city VARCHAR(50), 
	is_default BOOLEAN, 
	latitude FLOAT, 
	longitude FLOAT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_addresses_id ON addresses (id);
CREATE TABLE orders (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	total_amount FLOAT NOT NULL, 
	status VARCHAR(30), 
	created_at DATETIME, 
	items_summary TEXT, 
	delivery_address_id INTEGER, 
	spice_level VARCHAR(20), 
	loyalty_coins_earned INTEGER, 
	loyalty_coins_spent INTEGER, 
	discount_amount FLOAT, 
	delivery_fee FLOAT, 
	gst_amount FLOAT, 
	payment_status VARCHAR(20), 
	payment_method VARCHAR(50), 
	razorpay_order_id VARCHAR(100), 
	razorpay_payment_id VARCHAR(100), 
	estimated_delivery DATETIME, 
	delivered_at DATETIME, 
	is_subscription_order BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(delivery_address_id) REFERENCES addresses (id)
);
CREATE INDEX ix_orders_id ON orders (id);
CREATE TABLE subscriptions (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	plan_type VARCHAR(30) NOT NULL, 
	is_active BOOLEAN, 
	start_date DATE, 
	end_date DATE, 
	paused_from DATE, 
	paused_until DATE, 
	delivery_address_id INTEGER, 
	preferred_time VARCHAR(20), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(delivery_address_id) REFERENCES addresses (id)
);
CREATE INDEX ix_subscriptions_id ON subscriptions (id);
CREATE TABLE order_items (
	id INTEGER NOT NULL, 
	order_id INTEGER, 
	item_id INTEGER, 
	quantity INTEGER, 
	price_at_order FLOAT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id), 
	FOREIGN KEY(item_id) REFERENCES menu_items (id)
);
CREATE INDEX ix_order_items_id ON order_items (id);
CREATE TABLE coin_ledger (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	amount INTEGER NOT NULL, 
	transaction_type VARCHAR(20) NOT NULL, 
	description VARCHAR(200), 
	order_id INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id)
);
CREATE INDEX ix_coin_ledger_id ON coin_ledger (id);
