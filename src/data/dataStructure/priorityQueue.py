from typing import Any

class PriorityQueueNode:
  """
  Priority Queue which contains a value and a priority.
  """

  def __init__(self, value: Any, priority: float) -> None:
    self.value = value
    self.priority = priority

class PriorityQueue:
  """
  Minimum priority queue.
  """

  def __init__(self) -> None:
    self.queue = list()
    
  def insert(self, node : PriorityQueueNode) -> None:
    """
    Insert node by priority.
    """

    if self.size() == 0:
      self.queue.append(node)
    else:
      for x in range(0, self.size()):
        if node.priority >= self.queue[x].priority:
          if x == (self.size() - 1):
            self.queue.insert(x + 1, node)
          else:
            continue
        else:
          self.queue.insert(x, node)
          return

  def pop(self) -> PriorityQueueNode:
    """
    Removes and returns the first value from the queue.
    """

    return self.queue.pop(0)
  
  def head(self) -> PriorityQueueNode:
    """
    Returns the first value from the queue.
    """
    return self.queue[0]
  
  def contains(self, value: Any) -> bool:
    """
    Returns if value is present in the queue.
    """

    return value in [elem.value for elem in self.queue]

  def size(self) -> int:
    """
    Returns the count of the elements in the queue.
    """

    return len(self.queue)
  
  def isEmpty(self) -> bool:
    """
    Returns if the queue is empty.
    """

    return self.size() == 0
  
  def getValues(self) -> list[Any]:
    """
    Retrieves the values from the queue.
    """

    return [e.value for e in self.queue]