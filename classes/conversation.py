class Conversation:
    _id_counter = 0

    @classmethod
    def next_id(cls):
        cls._id_counter += 1
        return cls._id_counter

    def __init__(self, clip_id, messages, speakers=None):
        """
        Initialize a conversation.
        
        Args:
            clip_id: ID of the clip this conversation belongs to
            messages: List of [speaker, text] pairs
            speakers: Optional set of speaker names (will be extracted from messages if not provided)
        """
        self.id = self.next_id()
        self.clips = [clip_id]
        self.messages = messages if messages else []
        
        # Extract speakers from messages if not provided
        if speakers is None:
            speakers = set()
            for msg in self.messages:
                if isinstance(msg, list) and len(msg) >= 1:
                    speakers.add(msg[0])  # First element is the speaker
        self.speakers = speakers if isinstance(speakers, set) else set(speakers)
    
    def add_messages(self, messages):
        """
        Add new messages to this conversation, skipping duplicates.
        
        Args:
            messages: List of [speaker, text] pairs to add
        """
        if not messages:
            return
        
        # Create a set of existing messages for fast duplicate checking
        # Use tuple (speaker, text) as the key for comparison
        existing_messages = set()
        for msg in self.messages:
            if isinstance(msg, list) and len(msg) >= 2:
                existing_messages.add((msg[0], msg[1]))
        
        # Add only new messages (not duplicates)
        new_messages = []
        for msg in messages:
            if isinstance(msg, list) and len(msg) >= 2:
                msg_tuple = (msg[0], msg[1])
                if msg_tuple not in existing_messages:
                    existing_messages.add(msg_tuple)
                    new_messages.append(msg)
                    self.speakers.add(msg[0])
        
        # Extend with only the new messages
        if new_messages:
            self.messages.extend(new_messages)
    
    def add_clip(self, clip_id):
        """
        Add a clip ID to this conversation's clips list.
        
        Args:
            clip_id: ID of the clip to add
        """
        if clip_id not in self.clips:
            self.clips.append(clip_id)
    
    def __repr__(self):
        """
        String representation of the conversation.
        """
        speakers_str = ", ".join(sorted(self.speakers)) if self.speakers else "none"
        clips_str = ", ".join(map(str, sorted(self.clips)))
        return f"Conversation(id={self.id}, clips=[{clips_str}], speakers=[{speakers_str}], messages={len(self.messages)})"