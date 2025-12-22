from utils.llm import get_embedding

class BaseNode:
    """Base class for all node types with integer IDs."""
    _id_counter = 0

    @classmethod
    def next_id(cls):
        cls._id_counter += 1
        return cls._id_counter

    def __init__(self, name):
        self.name = name
        self.id = self.next_id()
        
    @property
    def type(self):
        return self.__class__.__name__

    def __repr__(self):
        return f"{self.type}(id={self.id})"


class CharacterNode(BaseNode):

    def __init__(self, name):
        super().__init__(name)

class ObjectNode(BaseNode):
    
    def __init__(self, name, owner=None, attribute=None, embedding=None):
        super().__init__(name)
        self.owner = owner
        self.attribute = attribute
        if attribute is not None:
            self.embedding = get_embedding(attribute + " " + name)
        else:
            self.embedding = get_embedding(name)

    def get_owner(self):
        """Get the owner of this object."""
        return self.owner
    
    def get_attribute(self):
        """Get the attribute of this object."""
        return self.attribute




