#!/usr/bin/env python3

from collections import ChainMap
from collections.abc import MutableMapping

class DictOverlay(MutableMapping):
    """A dict-like object that only writes pending changes to the underlying dict on .flush().

    This is a dict-like object which, instead of storing changes in the underlying dict,
    keeps them in a staging area (a second dict) which is only flushed to the underlying
    base dict when the user calls .flush().
    """

    # A unique object that represents a pending deletion from the DictOverlay.
    class _DELETED:
        def __repr__(self):
            return "DELETED"
    _DELETED = _DELETED()

    def __init__(self, base):
        self.base = base
        self.staged = {}

        # Since this will have to take into account pending additions and deletions, track it
        # ourselves so that we don't have to recalculate it every time someone calls len()
        self.len = len(self.base)

        # This is where the changes get overlayed on the base.  Lookups in self.values will
        # result in a value from self.staged if one is present, and otherwise will fall through
        # to self.base.
        self.values = ChainMap(self.staged, self.base)

    def flush(self):
        """Write pending changes to the underlying dictionary.
        """
        for key, value in self.staged.items():
            # Apply pending deletions
            if value is self._DELETED:
                if key in self.base:
                    del self.base[key]
        
            # Apply pending writes
            else:
                self.base[key] = value

        self.staged.clear()

    def reset(self):
        """Discard all pending changes.

        This reverts the OverlayDict to its state the last time it was last flush()ed or at its
        creation, whichever is more recent.
        """
        self.staged.clear()
        self.len = len(self.base)

    def changed(self):
        return (k if self[k] is not self._DELETED for k in self.staged)

    def deleted(self):
        return (k if self[k] is self._DELETED for k in self.staged)

    def __repr__(self):
        return f"{self.__class__.__name__}(base={self.base!r}, changes={self.staged!r})"

    ############################################################
    # Abstract method implementations required by MutableMapping
    
    def __getitem__(self, key):
        value = self.values[key]

        # Unflushted deletions should look like the key is absent.
        if value is self._DELETED:
            raise KeyError(key)

        return value

    def __setitem__(self, key, value):
        if key not in self.values:
            self.len += 1

        self.staged[key] = value 

    def __delitem__(self, key):
        # Deleted keys should appear nonexistent; this means that deleting them a second
        # time should result in a KeyError
        if key not in self.values or self.values[key] is self._DELETED:
            raise KeyError(key)

        self.staged[key] = self._DELETED
        self.len -= 1

    def __len__(self):
        return self.len

    def __iter__(self):
        for key, value in self.values.items():
            if value is not self._DELETED:
                yield key
