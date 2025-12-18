
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

    def __init__(self, name, faces=None):
        super().__init__(name)
        self.faces = faces or []
    
    def add_face(self, face):
        """
        Add a face to this character.
        
        Args:
            face: Face dictionary with 'embedding', 'bbox', 'confidence', and optionally 'track_id'
        """
        self.faces.append(face)
    
    def get_faces(self):
        """Get all faces for this character."""
        return self.faces
    
    def num_faces(self):
        """Get the number of faces for this character."""
        return len(self.faces)


class ObjectNode(BaseNode):
    
    def __init__(self, name, owner=None, attribute=None):
        super().__init__(name)
        self.owner = owner
        self.attribute = attribute

    def get_owner(self):
        """Get the owner of this object."""
        return self.owner
    
    def get_attribute(self):
        """Get the attribute of this object."""
        return self.attribute




