# TPRG2131 Winter 2017 Project 2 Database management
# Louis Bertrand <louis.bertrand@durhamcollege.ca>
# March 28, 2017
#
# Define useful functions to manage measurement data in a relational database
# 


class DatabaseConnector(object):
    """Manage creating measurement, sensor, type and units records in SQLite DB. 
    """
    def __init__(self, database):
        """Initialize the sqlite database and prepare to store measurements.
        
        This is for testing therefore the database is created new.
        """
        import sqlite3

        self._connection = self._create_database(database)

        # Initialize dictionaries to remember units, types and sensors
        self._units = {}
        self._types = {}
        self._sensors = {}
        return

    def _create_database(self, filename):
        """Create SQLite measurement DB, drop existing tables if any, and rebuild.
        
        Warning: This function will delete any data already in the database!
        Returns a sqlite3.Connection to the database.
        
        The general pattern in SQL is drop the table if it exists, then 
        create the table again with the specific columns and constraints
        required by the application.
        Note: the  (back tick) character quoting the table and column names
        is optional in SQL but was added by the SQLite browser. The quote marks
        were copied along with the SQL statements generated by the browser 
        application. 
        """

        # open the file, file will be created if it doesn't already exist
        conn = sqlite3.Connection(filename)
        # Get a cursor
        curs = conn.cursor()
        
        # Measurement table
        sql = """
        DROP TABLE IF EXISTS measurement;
        CREATE TABLE measurement (
        timestamp	TEXT NOT NULL,
        sensor	INTEGER NOT NULL,
        value	REAL NOT NULL,
        PRIMARY KEY(timestamp,sensor),
        FOREIGN KEY(sensor) REFERENCES sensor(id)
        );"""
        curs.executescript(sql)

        # Sensor table
        sql = """
        DROP TABLE IF EXISTS sensor;
        CREATE TABLE sensor (
        id	INTEGER,
        name	TEXT NOT NULL UNIQUE,
        type	INTEGER NOT NULL,
        PRIMARY KEY(id),
        FOREIGN KEY(type) REFERENCES type(id)
        );"""
        curs.executescript(sql)

        # Type table
        sql ="""
        DROP TABLE IF EXISTS type;
        CREATE TABLE type (
        id	INTEGER,
        name	TEXT NOT NULL UNIQUE,
        units	INTEGER,
        PRIMARY KEY(id),
        FOREIGN KEY(units) REFERENCES units(id)
        );"""
        curs.executescript(sql)

        # Units table
        sql = """
        DROP TABLE IF EXISTS units;
        CREATE TABLE units (
        id	INTEGER,
        name	TEXT NOT NULL UNIQUE,
        PRIMARY KEY(id)
        );"""
        curs.executescript(sql)

        # Write the changes to the database file
        conn.commit()
        return conn

    def store_measurement(self, meas):
        """Create a new record in the measurement table for this measurement.

        meas is a Measurement instance.
        """
        curs = self._connection.cursor()
        
        # Get the row ID for this sensor; get_id() returns a name string
        name_id = self._sensors[meas.get_id()]
        # Insert the new record
        curs.execute("""INSERT INTO measurement (timestamp, sensor, value)
            VALUES (?, ?, ?);""", (meas.get_timestamp(), name_id, meas.get_data()))
        self._connection.commit()
        return
        

    def register_sensor(self, sensor):
        """Create DB records for units, type and sensor name for this sensor.
        
        The order in which items are created in the database depends on the
        primary key to foreign key relationship. The primary key row must exist
        before a foreign key can refer to it.
        The order is units, type, name. After that, measurements can be entered
        into the measurement table with a single insert.
        The DatabaseConnector remembers the row ids to create new records quickly.
        """
        def insert_and_recall_id(items, table, cols, id_dict):
            """Nested function: Insert items into table at cols and return ID."""
            if len(items) == 2 and len(cols) == 2:
                sql = """INSERT OR IGNORE INTO {} ({}, {}) 
                    VALUES (?,?)""".format(table, cols[0],cols[1])
                curs.execute(sql, items)
            else:
                sql = "INSERT OR IGNORE INTO {} ({}) VALUES (?)".format(table, cols[0])
                curs.execute(sql, items)
            # what is the ID corresponding to the items just entered?
            sql = "SELECT id FROM {} WHERE name = ?".format(table)
            curs.execute(sql, (items[0],))
            item_id = curs.fetchone()[0]  # Fetch the first row and get element [0]
            # Remember this id
            if items[0] not in id_dict:
                id_dict[items[0]] = item_id
            return item_id

        curs = self._connection.cursor()

        # Use the nested function for the units, type and name 
        # Units name into units table
        units_id = insert_and_recall_id((sensor.get_units(),), "units", ("name",), self._units)
        # Type name and units into type table
        type_id = insert_and_recall_id((sensor.get_type(), units_id),\
            "type", ("name","units"), self._types)
        # Sensor name and type into sensor table
        sensor_id = insert_and_recall_id((sensor.get_name(), type_id),\
            "sensor", ("name","type"), self._sensors)

        self._connection.commit() # commit the transaction
        return



class PostgreSQLConnector(object):
    """Manage creating measurement, sensor, type and units records in the database. 
    """
    def __init__(self, dbname, host, user, password):
        """Initialize the PostgreSQL database connection.
        """
        import psycopg2
        #postgresql://[user[:password]@][netloc][:port][/dbname][?param1=value1&...]
        #https://www.postgresql.org/docs/current/static/libpq-connect.html#LIBPQ-CONNSTRING
        dsn = "postgresql://{}:{}@{}/{}".format(user, password, host, dbname)
        self._connection = psycopg2.connect(dsn)
        # Initialize dictionaries to remember units, types and sensors
        self._units = {}
        self._types = {}
        self._sensors = {}
        return
#
    def store_measurement(self, meas):
        """Create a new record in the measurement table for this measurement.

        meas is a Measurement instance.
        """
        curs = self._connection.cursor()
        
        # Get the row ID for this sensor; get_id() returns a name string
        name_id = self._sensors[meas.get_id()]
        # Insert the new record
        curs.execute("""INSERT INTO measurement (timestamp, sensor, value)
            VALUES (%s, %s, %s);""", (meas.get_timestamp(), name_id, meas.get_data()))
        self._connection.commit()
        return

    def register_sensor(self, sensor):
        """Create DB records for units, type and sensor name for this sensor.
        
        The order in which items are created in the database depends on the
        primary key to foreign key relationship. The primary key row must exist
        before a foreign key can refer to it.
        The order is units, type, name. After that, measurements can be entered
        into the measurement table with a single insert.
        The DatabaseConnector remembers the row ids to create new records quickly.
        """
        def insert_and_recall_id(items, table, cols, constraint, id_dict):
            """Nested function: Insert items into table at cols and return ID."""
            if len(items) == 2 and len(cols) == 2:
                sql = """INSERT INTO {} ({}, {}) 
                    VALUES (%s,%s)
                    ON CONFLICT ON CONSTRAINT {} DO NOTHING;
                    """.format(table, cols[0],cols[1], constraint)
                curs.execute(sql, items)
            else:
                sql = """INSERT INTO {} ({}) VALUES (%s)
                    ON CONFLICT ON CONSTRAINT {} DO NOTHING;
                    """.format(table, cols[0], constraint)
                curs.execute(sql, items)
            # what is the ID corresponding to the items just entered?
            sql = "SELECT id FROM {} WHERE name = %s".format(table)
            curs.execute(sql, (items[0],))
            item_id = curs.fetchone()[0]  # Fetch the first row and get element [0]
            # Remember this id
            if items[0] not in id_dict:
                id_dict[items[0]] = item_id
            return item_id

        curs = self._connection.cursor()

        # Use the nested function for the units, type and name 
        # Units name into units table
        units_id = insert_and_recall_id((sensor.get_units(),), "units", ("name",), "units_name_key", self._units)
        # Type name and units into type table
        type_id = insert_and_recall_id((sensor.get_type(), units_id),\
            "type", ("name","units"), "type_name_key", self._types)
        # Sensor name and type into sensor table
        sensor_id = insert_and_recall_id((sensor.get_name(), type_id),\
            "sensor", ("name","type"), "sensor_name_key", self._sensors)

        self._connection.commit() # commit the transaction
        return

