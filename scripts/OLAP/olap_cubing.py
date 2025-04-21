"""
Module 6: OLAP and Cubing Script
File: scripts/olap_cubing.py

A cube is a precomputed, multidimensional structure 
where data is aggregated across all possible 
combinations of selected dimensions 
(e.g., DayOfWeek, ProductID).

Purpose: It allows for fast querying and analysis 
across many dimensions without needing to 
compute aggregations on the fly.
Structure: The result is stored as a 
multidimensional dataset that can be 
queried with SQL-like syntax 
or visualized in BI tools.


This example script handles OLAP cubing with Python. 
It ingests data from a data warehouse,
performs aggregations for multiple dimensions, 
and creates OLAP cubes. 
The cubes are saved as CSV files for further analysis.
Cubes might also be kept in Power BI, Snowflake, Looker, or another tool.

Input Data:

- A fact table (sales): Includes sale_date, product_id, customer_id, sale_amount, etc.
- Dimension tables: Define attributes like products, customers, and more

Output Cube:

- The cube contains precomputed totals, averages, counts, 
and other metrics for all combinations of DayOfWeek, ProductID, and CustomerID.

AFTER CREATION, we can Query the Cube:

- Slice: e.g., Extract sales for a specific customer (or specific store or region, depending on your data).
- Dice: e.g., Filter sales for specific combinations of ProductID and other (e.g., store, region, campaign, depending on your data)
- Drill-down: e.g., Aggregate sales by DayOfWeek (within a specific store or region, depending on your data)

IMPORTANT: The OLAP cubing script needs to align 
with your data warehouse (DW) structure and 
the etl_to_dw.py script that defines your database schema. 

THIS EXAMPLE INPUTS DIMENSION AND FACT TABLES:

This example assumes a simple data warehouse structure with one fact table (`sale`) 
and two dimension tables (`product` and `customer`). These tables collectively enable 
multidimensional analysis using OLAP cubing.

DIMENSION TABLES:

product table example

   product_id,name,category,unit_price_usd
   101,laptop,Electronics,793.12
   102,hoodie,Clothing,39.10
   103,cable,Electronics,22.76

customer table example

   customer_id,name,region,join_date
   1001,William White,East,2021-11-11
   1002,Wylie Coyote,East,2023-02-14
   1003,Dan Brown,West,2023-10-19

FACT TABLE:

sale table example
   sale_id,customer_id,product_id,sale_date,sale_amount_usd
   550,1001,101,2024-01-06,6344.96
   551,1002,102,2024-01-06,312.80
   552,1003,103,2024-01-16,431.00


THIS EXAMPLE OUTPUTS:

This example assumes a cube data set with the following column names (yours will differ).
DayOfWeek,product_id,customer_id,sale_amount_usd_sum,sale_id_count,sale_ids
Friday,101,1001,6344.96,1,[582]
etc.

"""

import pandas as pd
import sqlite3
import pathlib
import sys

# For local imports, temporarily add project root to Python sys.path
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.logger import logger  # noqa: E402

# Constants
DW_DIR: pathlib.Path = pathlib.Path("data").joinpath("dw")
DB_PATH: pathlib.Path = DW_DIR.joinpath("smart_sales.db")
OLAP_OUTPUT_DIR: pathlib.Path = pathlib.Path("data").joinpath("olap_cubing_outputs")

# Create output directory if it does not exist
OLAP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def ingest_sales_data_from_dw() -> pd.DataFrame:
    """Ingest sales data from SQLite data warehouse."""
    try:
        conn = sqlite3.connect(DB_PATH)
        sales_df = pd.read_sql_query("SELECT * FROM sale", conn)
        conn.close()
        logger.info("Sales data successfully loaded from SQLite data warehouse.")
        return sales_df
    except Exception as e:
        logger.error(f"Error loading sale table data from data warehouse: {e}")
        raise


def create_olap_cube(
    sales_df: pd.DataFrame, dimensions: list, metrics: dict
) -> pd.DataFrame:
    """
    Create an OLAP cube by aggregating data across multiple dimensions.

    Args:
        sales_df (pd.DataFrame): The sales data.
        dimensions (list): List of column names to group by.
        metrics (dict): Dictionary of aggregation functions for metrics.

    Returns:
        pd.DataFrame: The multidimensional OLAP cube.
    """
    try:
        # Group by the specified dimensions and aggregate metrics
        # When we use the groupby() method in Pandas, 
        # it creates a hierarchical index (also known as a MultiIndex) for the grouped data. 
        # This structure reflects the grouping levels but can make the resulting DataFrame 
        # harder to interact with, especially for tasks like slicing, querying, or merging data. 
        # Converting the hierarchical index into a flat table by calling reset_index()
        # simplifies our operations.

        # NOTE: Pandas generates hierarchical column names when we specify 
        # multiple aggregation functions for a single column. 
        # If we specify only one aggregation function per column, 
        # the resulting column names will not include the suffix.

        # Group by the specified dimensions
        grouped = sales_df.groupby(dimensions)

        # Perform the aggregations
        cube = grouped.agg(metrics).reset_index()

        # Add a list of sale IDs for traceability
        cube["sale_ids"] = grouped["transaction_id"].apply(list).reset_index(drop=True)

        # Generate explicit column names
        explicit_columns = generate_column_names(dimensions, metrics)
        explicit_columns.append("sale_ids")  # Include the traceability column
        cube.columns = explicit_columns

        logger.info(f"OLAP cube created with dimensions: {dimensions}")
        return cube
    except Exception as e:
        logger.error(f"Error creating OLAP cube: {e}")
        raise

def generate_column_names(dimensions: list, metrics: dict) -> list:
    """
    Generate explicit column names for OLAP cube, ensuring no trailing underscores.
    
    Args:
        dimensions (list): List of dimension columns.
        metrics (dict): Dictionary of metrics with aggregation functions.
        
    Returns:
        list: Explicit column names.
    """
    # Start with dimensions
    column_names = dimensions.copy()
    
    # Add metrics with their aggregation suffixes
    for column, agg_funcs in metrics.items():
        if isinstance(agg_funcs, list):
            for func in agg_funcs:
                column_names.append(f"{column}_{func}")
        else:
            column_names.append(f"{column}_{agg_funcs}")
    
    # Remove trailing underscores from all column names
    column_names = [col.rstrip("_") for col in column_names]
    
    return column_names
    

def write_cube_to_csv(cube: pd.DataFrame, filename: str) -> None:
    """Write the OLAP cube to a CSV file."""
    try:
        output_path = OLAP_OUTPUT_DIR.joinpath(filename)
        cube.to_csv(output_path, index=False)
        logger.info(f"OLAP cube saved to {output_path}.")
    except Exception as e:
        logger.error(f"Error saving OLAP cube to CSV file: {e}")
        raise


def main():
    """Main function for OLAP cubing."""
    logger.info("Starting OLAP Cubing process...")

    # Step 1: Ingest sales data
    sales_df = ingest_sales_data_from_dw()

    # Step 2: Add additional columns for time-based dimensions
    sales_df["sale_date"] = pd.to_datetime(sales_df["sale_date"])
    sales_df["DayOfWeek"] = sales_df["sale_date"].dt.day_name()
    sales_df["Month"] = sales_df["sale_date"].dt.month
    sales_df["Year"] = sales_df["sale_date"].dt.year
    sales_df["Quarter"] = sales_df["sale_date"].dt.quarter

    # Step 3: Define dimensions and metrics for the cube
    dimensions = ["Quarter", "product_id", "customer_id"]
    metrics = {
        "sale_amount_usd": ["sum", "mean"],
        "transaction_id": "count"
    }

    # Step 4: Create the cube
    olap_cube = create_olap_cube(sales_df, dimensions, metrics)

    # Step 5: Save the cube to a CSV file
    write_cube_to_csv(olap_cube, "multidimensional_olap_cube.csv")

    logger.info("OLAP Cubing process completed successfully.")
    logger.info(f"Please see outputs in {OLAP_OUTPUT_DIR}")


if __name__ == "__main__":
    main()