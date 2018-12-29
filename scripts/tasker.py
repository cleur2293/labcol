import logging
from dataclasses import dataclass
from typing import List
from typing import Dict
from random import randrange
logger = logging.getLogger(__name__) # Creating logger for logging across this module

from scripts import PSQL

@dataclass
class Person:
    person_id: str
    person_name: str
    person_surname: str
    person_email: str
    current_task: int = 0 #id of the task
    completed_tasks: List[int] = () # list with ids of completed tasks
    is_done: bool = False

    def next_task(self):
        return "next_task"

    def check_answer(self):
        return True


@dataclass
class All_persons:
    persons: Dict[str,Person] # Dict of Person objects, person_ids as keys

    def addPerson(self,person_id,person_name,person_surname,person_email):
        new_person = Person(person_id,person_name,person_surname,person_email)
        self.persons[str(person_id)] = new_person

        logger.info(f'User \'{person_name} {person_surname}\' created successfully: {new_person}')

        return True


    def is_exist(self,person_id: str) -> bool:
        return person_id in self.persons

@dataclass
class Tasker:
    database_handler: PSQL.PSQL
    tasks = [100,200,300,400]


    @classmethod
    def get_random_task(self, psql_obj: PSQL.PSQL):



        #return self.tasks[randrange(len(self.tasks))]

        sql_req = """SELECT id,task,answer,variants,picture_path FROM ciscolive.interview.tasks"""

        sql_data = None

        logger.info(str(psql_obj.psql_request(sql_req, sql_data)))

        rows = psql_obj.cur.fetchall()

        logger.debug('rows:{}'.format(str(rows)))

        return rows[randrange(len(rows))]

    @classmethod
    def assign_task(self, psql_obj: PSQL.PSQL, person_id: str,task_id: int, loc_answer: int) -> bool:
        sql_req = """\
        INSERT INTO ciscolive.interview.assigned_tasks
        (person_id,task_id,loc_answer)
        VALUES (%s, %s, %s);"""

        sql_data = (person_id,task_id,loc_answer)

        logger.info(sql_req)
        try:

            logger.info(psql_obj.psql_request(sql_req, sql_data))
        except Exception:
            return False

        psql_obj.Commit()

        return True

    @classmethod
    def has_task(self, psql_obj: PSQL.PSQL, person_id: str) -> bool:

        sql_req = """\
        SELECT task_id FROM ciscolive.interview.assigned_tasks
        WHERE person_id = %s ORDER BY epoch DESC;"""

        sql_data = (str(person_id),)

        logger.info(sql_req)

        logger.info(psql_obj.psql_request(sql_req, sql_data))

        rows = psql_obj.cur.fetchall()

        logger.debug('rows:{}'.format(str(rows)))

        if (len(rows) > 0):
            return rows[0]['task_id']
        else:
            return False

    @classmethod
    def get_assigned_task_by_id(self,psql_obj,person_id: str, task_id: int) -> Dict:
        sql_req = """SELECT id,task,answer,variants,picture_path FROM ciscolive.interview.tasks WHERE id = %s"""

        sql_data = (task_id,)

        logger.info(str(psql_obj.psql_request(sql_req, sql_data)))

        row = psql_obj.cur.fetchone()

        logger.debug('row:{}'.format(str(row)))

        return row
