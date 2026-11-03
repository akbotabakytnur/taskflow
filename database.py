import psycopg2


def get_connection():
    connection = psycopg2.connect(
        host="localhost",
        database="taskflow",
        user="postgres",
        password="610202418"
    )

    return connection