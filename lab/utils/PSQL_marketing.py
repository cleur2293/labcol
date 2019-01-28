import psycopg2
import psycopg2.extras

import logging

logger = logging.getLogger(__name__) # Creating logger for logging across this module

import re

class PSQL:
    def __init__(self, dbname='ciscolive',host='10.81.127.49',user='ciscolive',password='cisco.123',conn=None):

        self.dbname = dbname
        self.host = host
        self.user = user
        self.password = password

        if (conn is not None):
            # conn - if we want to create PSQL object as part of existed connection (needed for multithreading purposes)
            self.cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            self.cur2 = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        else:
            try:
                self.conn = self.connectToSQL()
            except psycopg2.OperationalError as e:
                logger.error('Error happened:{}'.format(str(e)[:50]))

                if (e.args[0][:27] == 'could not connect to server'):
                    # Connection timeout error
                    raise IndexError

                elif (e.args[0][:12] == 'FATAL:  role'):
                    # Incorrect login
                    raise ValueError

                else:
                    raise Exception

            else:
                self.cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                self.cur2 = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def getConn(self):
        return self.conn

    def connectToSQL(self):
        """
        Main function to connect to Zabbix PSQL DB
        :return:
        """

        try:
            conn = psycopg2.connect(dbname=self.dbname,host=self.host,user=self.user,password=self.password,port = 5432)

        except psycopg2.OperationalError as e:
            raise e # propagate e further
        else:
            return conn

    def Commit(self) -> bool:
        logger.info('Commit done')
        self.conn.commit()

    def psql_request(self,sql_req,sql_data=None):
        """
        PSQL Zabbix Request with logging
        :param sql_req: request with variables
        :param sql_data: variables values
        :return: psycopg2 statusmessage
        """
        try:
            # cur.execute("""SELECT * from skynet.cdp_neighbors""")
            self.cur.execute(sql_req,sql_data)
            logger.info(f'PSQL request: {self.cur.query}')


        except Exception as exc:
            logger.error('ERROR during SQL request:{}'.format(str(exc)))

        return self.cur.statusmessage

    def psql_request2(self,sql_req,sql_data=None):
        """
        PSQL Zabbix Request with logging
        :param sql_req: request with variables
        :param sql_data: variables values
        :return: psycopg2 statusmessage
        """
        try:
            # cur.execute("""SELECT * from skynet.cdp_neighbors""")
            self.cur2.execute(sql_req,sql_data)
            logger.info(f'PSQL request: {self.cur2.query}')


        except Exception as exc:
            logger.error('ERROR during SQL request:{}'.format(str(exc)))

        return self.cur2.statusmessage

    def psql_request_silent(self,sql_req,sql_data=None):
        """
        The same as ZabbixRequest but without logging (for PSQL logger handler
        don't product to much noise)
        :param sql_req: request with variables
        :param sql_data: variables values
        :return: psycopg2 statusmessage
        """
        try:
            # cur.execute("""SELECT * from skynet.cdp_neighbors""")
            self.cur.execute(sql_req,sql_data)

        except Exception as exc:
            logger.error('ERROR during SQL request:{}'.format(str(exc)))

        return self.cur.statusmessage

    def get_assigned_tasks(self):
        sql_req = """SELECT * FROM ciscolive.marketing.tasks"""

        sql_data = None

        logger.info(str(self.psql_request(sql_req, sql_data)))

        rows = self.cur.fetchall()

        logger.debug('rows:{}'.format(str(rows)))

        return rows

    def add_person(self,person_id : str,person_name: str,person_surname: str,
                   person_email: str, room_id: str) -> bool:
        sql_req = """\
        INSERT INTO ciscolive.marketing.persons
        (id,name,surname,email,room_id)
        VALUES (%s, %s, %s, %s, %s);"""

        sql_data = (person_id,person_name,person_surname,person_email,room_id)

        logger.info(sql_req)
        try:

            logger.info(self.psql_request(sql_req, sql_data))
        except Exception:
            return False

        self.Commit()

        return True

    def add_received_photos(self,task_id, person_id: str, filename: str) -> int:
        sql_req = """\
        INSERT INTO ciscolive.marketing.received_content
        (task_id,person_id,received_photos)
        VALUES (%s, %s, %s) RETURNING epoch;"""

        sql_data = (task_id,person_id,filename)

        logger.info(sql_req)
        try:

            logger.info(self.psql_request(sql_req, sql_data))
        except Exception:
            return -1

        self.Commit()

        return self.cur.fetchone()['epoch']

    def add_received_links(self, task_id, person_id: str, link: str) -> int:
        sql_req = """\
        INSERT INTO ciscolive.marketing.received_content
        (task_id,person_id,received_links)
        VALUES (%s, %s, %s) RETURNING epoch;"""

        sql_data = (task_id, person_id, link)

        logger.info(sql_req)
        try:

            logger.info(self.psql_request(sql_req, sql_data))
        except Exception:
            return -1

        self.Commit()

        return self.cur.fetchone()['epoch']

    def is_person_exists(self,person_id: str) -> bool:
        sql_req = """SELECT * FROM ciscolive.marketing.persons WHERE id = %s"""

        sql_data = (str(person_id),)

        logger.info(str(self.psql_request(sql_req, sql_data)))

        row = self.cur.fetchone()

        logger.debug('rows:{}'.format(str(row)))

        return bool(row)
