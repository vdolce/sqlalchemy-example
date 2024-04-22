import logging
import os

import psycopg2

DB_CONFIG = {
    "database": os.environ.get("POSTGRES_DB"),
    "user": os.environ.get("POSTGRES_USER"),
    "host": os.environ.get("POSTGRES_DB"),
    "password": os.environ.get("POSTGRES_PASSWORD"),
    "port": os.environ.get("POSTGRES_PORT"),
}


from db.base import engine
from sqlalchemy import text

def execute_query(query, params=None):
    with engine.connect() as conn:
        return conn.execute(text(query), params)


def execute_insert_query(query, params=None):
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        conn.commit()
        return result



def execute_insert_queries(query, params_tuple=None):
    with psycopg2.connect(**DB_CONFIG) as conn:
        cur = conn.cursor()
        cur.executemany(query, params_tuple)
        conn.commit()


def get_customers():
    rows = execute_query("SELECT * FROM customer")
    return rows


def get_orders_of_customer(customer_id):
    rows = execute_query(
        """
        SELECT 
            item.name, 
            item.description, 
            item.price, 
            item.price*order_items.quantity AS total
        FROM orders 
        JOIN order_items 
        ON 
            order_items.order_id = orders.id 
        JOIN item
        ON 
            item.id = order_items.item_id
        WHERE
            orders.customer_id=%(customer_id)s
        """,
        {"customer_id": customer_id},
    )
    return rows


def get_total_cost_of_an_order(order_id):
    rows = execute_query(
        """
        SELECT 
            SUM(item.price*order_items.quantity) AS total
        FROM orders 
        JOIN order_items 
        ON 
            order_items.order_id = orders.id 
        JOIN item 
        ON 
            item.id = order_items.item_id
        WHERE
            orders.id=%(order_id)s
        """,
        {"order_id": order_id},
    )
    return rows


def get_orders_between_dates(after, before):
    rows = execute_query(
        """
        SELECT
            customer.name,
            item.name, 
            item.price, 
            item.price*order_items.quantity AS total
        FROM orders 
        JOIN customer
        ON
            customer.id = orders.customer_id
        JOIN order_items 
        ON 
            order_items.order_id = orders.id 
        JOIN item 
        ON 
            item.id = order_items.item_id
        WHERE
            orders.order_time >= %(after)s
        AND
            orders.order_time <= %(before)s
        """,
        {"after": after, "before": before},
    )
    return rows


def add_new_order_for_customer(customer_id, items):
    try:
        result = execute_insert_query(
            """
            INSERT INTO orders
                (customer_id, order_time)
            VALUES
                (:customer_id, NOW())
            RETURNING id
            """,
            {"customer_id": customer_id},
        )
        new_order_id = result.one().id

        (
            execute_insert_query(
                """
            INSERT INTO order_items
                (order_id, item_id, quantity)
            VALUES
                (:order_id, :item_id, :quantity)
            """,
                [
                    {
                        "order_id": new_order_id,
                        "item_id": item["id"],
                        "quantity": item["quantity"],
                    }
                    for item in items
                ],
            )
        )
        return True

    except Exception:
        logging.exception("Failed to add new order")
        return False
