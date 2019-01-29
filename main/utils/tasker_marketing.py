import logging
from dataclasses import dataclass
from typing import Dict
from random import randrange
logger = logging.getLogger(__name__) # Creating logger for logging across this module

from utils import PSQL

@dataclass
class Tasker:

    @classmethod
    def get_random_task(self, psql_obj: PSQL.PSQL, person_id: str) -> Dict:

        sql_req = """SELECT
        id, task
        FROM
        ciscolive.marketing.tasks
        WHERE id
        NOT
        IN(
        SELECT task_id
        FROM
        ciscolive.marketing.assigned_tasks
        WHERE
        person_id = %s
        );"""

        sql_data = (person_id,)

        logger.info(str(psql_obj.psql_request(sql_req, sql_data)))

        rows = psql_obj.cur.fetchall()

        logger.debug('rows:{}'.format(str(rows)))

        if len(rows) > 0:
            # If we have results to fetch
            return rows[randrange(len(rows))]
        else:
            return {}

    @classmethod
    def assign_task(self, psql_obj: PSQL.PSQL, person_id: str,task_id: int) -> bool:
        sql_req = """\
        INSERT INTO ciscolive.marketing.assigned_tasks
        (person_id,task_id)
        VALUES (%s, %s);"""

        sql_data = (person_id,task_id)

        logger.info(sql_req)
        try:

            logger.info(psql_obj.psql_request(sql_req, sql_data))
        except Exception:
            return False

        psql_obj.Commit()

        return True

    @classmethod
    def has_task(self, psql_obj: PSQL.PSQL, person_id: str) -> int:

        sql_req = """\
        SELECT task_id FROM ciscolive.marketing.assigned_tasks
        WHERE person_id = %s ORDER BY epoch DESC;"""

        sql_data = (str(person_id),)

        logger.info(sql_req)

        logger.info(psql_obj.psql_request(sql_req, sql_data))

        rows = psql_obj.cur.fetchall()

        logger.debug('rows:{}'.format(str(rows)))

        if (len(rows) > 0):
            return rows[0]['task_id']
        else:
            return -1

    @classmethod
    def get_assigned_task_by_id(self,psql_obj, task_id: int) -> Dict:
        sql_req = """SELECT id,task FROM ciscolive.marketing.tasks WHERE id = %s"""

        sql_data = (task_id,)

        logger.info(str(psql_obj.psql_request(sql_req, sql_data)))

        row = psql_obj.cur.fetchone()

        logger.debug('row:{}'.format(str(row)))

        return row


    @classmethod
    def get_assigned_tasks_by_person(self,psql_obj,person_id) -> Dict:
        sql_req = """SELECT task_id,epoch,person_id,status
         FROM ciscolive.marketing.assigned_tasks
         WHERE person_id = %s ORDER BY epoch DESC"""

        sql_data = (person_id,)

        logger.info(str(psql_obj.psql_request(sql_req, sql_data)))

        rows = psql_obj.cur.fetchall()

        logger.debug('rows:{}'.format(str(rows)))

        return rows

    @classmethod
    def get_received_links_by_person(self,psql_obj,person_id,task_id) -> Dict:
        sql_req = """SELECT * FROM ciscolive.marketing.received_content 
        WHERE task_id = %s
        AND person_id = %s 
        AND received_links IS NOT NULL
        ORDER BY epoch ASC"""

        sql_data = (task_id,person_id)

        logger.info(str(psql_obj.psql_request2(sql_req, sql_data)))

        rows = psql_obj.cur2.fetchall()

        logger.debug('rows:{}'.format(str(rows)))

        return rows

    @classmethod
    def get_received_link_by_person_epoch(self,psql_obj,person_id,task_id,epoch) -> Dict:
        sql_req = """SELECT * FROM ciscolive.marketing.received_content 
        WHERE task_id = %s
        AND person_id = %s 
        AND received_links IS NOT NULL
        AND epoch = %s"""

        sql_data = (task_id,person_id,epoch)

        logger.info(str(psql_obj.psql_request2(sql_req, sql_data)))

        rows = psql_obj.cur2.fetchall()

        logger.debug('rows:{}'.format(str(rows)))

        return rows[0]

    @classmethod
    def change_content_status(self,psql_obj,person_id,task_id,epoch,status) -> bool:

        if status == 'approved':
            sql_req = """UPDATE ciscolive.marketing.received_content 
            SET status = 'approved'
            WHERE person_id = %s
            AND task_id = %s
            AND epoch = %s"""

        elif status == 'rejected':
            sql_req = """UPDATE ciscolive.marketing.received_content 
            SET status = 'rejected'
            WHERE person_id = %s
            AND task_id = %s
            AND epoch = %s"""
        else:
            #Unknown status received
            return False

        sql_data = (person_id, task_id, epoch)

        logger.info(str(psql_obj.psql_request(sql_req, sql_data)))
        # committing changes
        psql_obj.Commit()

        return True

    @classmethod
    def get_all_users(self, psql_obj) -> Dict:
        sql_req = """SELECT * FROM ciscolive.marketing.persons WHERE room_id IS NOT NULL"""

        sql_data = ()

        logger.info(str(psql_obj.psql_request2(sql_req, sql_data)))

        rows = psql_obj.cur2.fetchall()

        logger.debug('rows:{}'.format(str(rows)))

        return rows

    @classmethod
    def get_task_status_by_person_id(self, psql_obj, person_id, task_id) -> bool:
        sql_req = """SELECT * FROM ciscolive.marketing.received_content WHERE person_id = %s
        AND task_id = %s
        AND status = 'approved'
        """

        sql_data = (person_id,task_id)

        logger.info(str(psql_obj.psql_request2(sql_req, sql_data)))

        rows = psql_obj.cur2.fetchall()
        logger.debug('rows:{}'.format(str(rows)))

        if len(rows) > 0:
            #If we have at least one photo or task approved
            return True
        else:
            return False


    @classmethod
    def get_task_runs(self, psql_obj) -> int:
        sql_req = """SELECT COUNT(*) FROM ciscolive.marketing.runs"""

        sql_data = ()

        logger.info(str(psql_obj.psql_request2(sql_req, sql_data)))
        task_runs = psql_obj.cur2.fetchone()

        return task_runs


    @classmethod
    def increment_task_run(self, psql_obj) -> int:
        sql_req = """INSERT INTO ciscolive.marketing.runs (run_count) VALUES (1)"""

        sql_data = ()

        logger.info(str(psql_obj.psql_request2(sql_req, sql_data)))
        psql_obj.Commit()

        task_runs = self.get_task_runs(psql_obj)

        logger.info(f'Incremented task runs to:{task_runs["count"]}')

        return task_runs
