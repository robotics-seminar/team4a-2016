from abc import ABCMeta, abstractmethod

"""
Generic class that describes a state. This class cannot be directly instantiated.
In addition to the following methods, every state should have the following fields:

currentInput: an integer that describes the input to the running state. For example,
              if the state represents searching for AprilTag 2, currentInput would be 2.
"""
class State():
    __metaclass__ = ABCMeta
    
    
    """
    Run one iteration of the state. Since the state machine itself handles looping,
    there is no need to implement that inside this method.
    """
    @abstractmethod
    def run(self):
        pass

    """
    Return the input to the next state.
    """
    @abstractmethod
    def nextInput(self):
        return None

    """
    Return the next state to run.
    """
    @abstractmethod
    def nextState(self):
        return None
        
    """
    Return whether the state is finished running and should transition to the next state.
    """
    @abstractmethod
    def isFinished(self):
        return False

    """
    Return whether this state is the last state to run.
    """
    @abstractmethod
    def isStopState(self):
        return False
