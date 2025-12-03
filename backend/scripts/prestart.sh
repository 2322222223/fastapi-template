#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python app/backend_pre_start.py

# Run migrations
alembic upgrade head

# Create initial data in DB
python app/initial_data.py

python app/initial_region_data.py

python app/initial_hot_search_data.py

python app/initial_product_data.py

python app/initial_product_detail_data.py

python app/initial_data_packages_data.py

python app/initial_membership_benefits_data.py

python app/initial_coupon_data.py

python app/initial_points_data.py

python app/initial_discovery_data.py

python app/initial_service_account_data.py

python app/initial_points_mall_data.py

