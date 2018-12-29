import logging
from dataclasses import dataclass
from typing import List
from typing import Dict
from typing import Any
from random import randrange


from scripts import setinitial
# Initializing logger
setinitial.setup_logging()
# create logger
logger = logging.getLogger(__name__)

from scripts import PSQL

@dataclass
class Transition:
    cur_state: str
    next_state: str
    inputs: List[str]
    actions: List[Any] = ()
    condition = lambda x: True # condition that needs to evaluate to true to move forward

    def do_next(self, input) -> str:
        if input in self.inputs and self.condition():
            logger.info(f'Moved from:{self.cur_state}->{self.next_state}')

            if self.actions:
                logger.info(f'Found actions, start executing it')
                for func in self.actions:
                    func
            else:
                logger.info(f'Not found actions')

            return self.next_state
        else:
            logger.info(f'Stayed in the current state:{self.cur_state}')
            return self.cur_state

    def is_match(self,input) -> bool:
        if input in self.inputs and self.condition():
            logger.info(f'Moved from:{self.cur_state}->{self.next_state}')
            return True
        else:
            logger.info(f'Stayed in the current state:{self.cur_state}')
            return False

    def create_condition(self, func):
        logger.info(f'Setting condition to: {func.name}')
        self.actions.append(func)

    def create_action(self, func):
        logger.info(f'Setting action to: {func.name}')
        self.condition = func

@dataclass
class Node:
    cur_state: str
    inputs: List[str]
    transitions: List[Transition]

    def action(self, func):
        logger.info('Start execution action')
        func()

    def transition(self, input: str) -> str:
        if input in self.inputs:
            for obj in [trans for trans in self.transitions if input in trans.inputs]:
                # return first transition where we found input
                return obj.do_next(input)
            logger.info(f'Stayed in the current state:{self.cur_state}')
            return self.cur_state
        else:
            logger.info(f'Stayed in the current state:{self.cur_state}')
            return self.cur_state

    def get_all_transitions(self):
        return [trans for trans in self.transitions]

    def add_transition(self,cur_state,next_state,inputs,actions=()):
        logger.info(f'Added transition. Trigger:{inputs}:{cur_state}->{next_state}')
        self.transitions.append(Transition(cur_state,next_state,inputs,actions))


@dataclass
class Workflow:
    cur_state: str
    nodes: Dict[str,Node]
    answers_count: int = 0

    def check_answer_count(self):
        return self.answers_count

    def process_input(self, input:str):
        logger.info(f'input="{input}"')

        #if input in [self.nodes.values()]:
        #    logger.info('Executing action')

        for transition in self.nodes[self.cur_state].transitions:

            if input in transition.inputs:
               if transition.condition():
                   self.cur_state = self.nodes[self.cur_state].transition(input)
                   logger.info(self.cur_state)

def ask_next_question(question_list:List[str]) -> str:
    logger.info('Your next question:AAA')

    return question_list[randrange(len(question_list))]

if __name__ == '__main__':

    questions = ['AAA','BBB','CCC','DDD','EEE',]

    i = 0

    trans1 = Transition("start_task","assign_task",["/START"])
    node_1 = Node("start_task",["/START"],[trans1])

    trans2 = Transition("assign_task","assign_task",["1","2","3","4","5"],[ask_next_question(questions)])
    trans3 = Transition("assign_task","finish_task",["1","2","3","4","5"])
    node_2 = Node("assign_task",["1","2","3","4","5"],[trans2,trans3])


    node_3 = Node("finish_task",[],[trans3])


    wf = Workflow("start_task",{"start_task":node_1,"assign_task":node_2,"finish_task":node_3})

    wf.process_input('/START')
    wf.process_input('1')





