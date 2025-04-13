# smart-store-miller

# Create virtual environment and activate

```shell
python -m venv .venv
```

```shell
.venv/Scripts/activate
```

# Install dependencies from requirements.txt

```shell
pip install -r requirements.txt
```

# Perpare data - navigate to scripts\data_preparation

```shell
py -m prepare_customers_data
py -m prepare_products_data
py -m prepare_sales_data
```

# Create Data Warehouse and push data into a star schema
```shell
py -m dw_create
py -m etl_to_dw
```

![alt text](image-1.png)


# Move to Power BI and analyze data
Here, we move to analyzing our data using SQL through PowerBI. In this example, we sum total sales per person to determine the top customers.

```shell
let
    Source = Odbc.Query("dsn=SmartSalesDSN", 
        "
        SELECT c.name, SUM(s.sale_amount_usd) AS total_spent 
        FROM sale s 
        JOIN customer c ON s.customer_id = c.customer_id 
        GROUP BY c.name 
        ORDER BY total_spent DESC
        "
    )
in
    Source
```

![alt text](image-2.png)

# Utilize Power BI to Create Visualizations

First, a bar chart of our top customers
![alt text](image-4.png)

Second, a line chart of sales per quarter, which can be sliced by category
![alt text](image-3.png)


