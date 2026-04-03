# wad.py
# WAD file loader — reads DOOM.WAD (or any IWAD/PWAD)
# Pure Python builtins only (struct, os)

import struct
import os


# WAD header
_HEADER_FMT  = '<4sii'   # id[4], numlumps, infotableofs
_HEADER_SIZE = 12

# Lump directory entry
_LUMP_FMT  = '<ii8s'     # filepos, size, name[8]
_LUMP_SIZE = 16


class Lump:
    """A single WAD lump: name + raw bytes."""
    __slots__ = ('name', 'data')

    def __init__(self, name: str, data: bytes):
        self.name = name
        self.data = data

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return f'Lump({self.name!r}, {len(self.data)} bytes)'


class WAD:
    """
    Loaded WAD file.

    Usage
    -----
    wad = WAD('DOOM.WAD')
    lump = wad.get_lump('E1M1')          # first lump named E1M1
    data = wad.get_lump_data('PLAYPAL')  # raw bytes
    map_lumps = wad.get_map_lumps('E1M1')  # ordered list of 11 lumps
    """

    def __init__(self, path: str):
        self.path   = path
        self.iwad   = False   # True if IWAD, False if PWAD
        self._lumps: list[Lump] = []
        self._index: dict[str, list[int]] = {}  # name → [lump indices]
        self._load(path)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def _load(self, path: str):
        if not os.path.isfile(path):
            raise FileNotFoundError(f'WAD not found: {path}')

        with open(path, 'rb') as f:
            raw = f.read()

        if len(raw) < _HEADER_SIZE:
            raise ValueError('File too small to be a WAD')

        magic, numlumps, dirofs = struct.unpack_from(_HEADER_FMT, raw, 0)

        if magic == b'IWAD':
            self.iwad = True
        elif magic == b'PWAD':
            self.iwad = False
        else:
            raise ValueError(f'Not a WAD file (magic={magic!r})')

        if dirofs + numlumps * _LUMP_SIZE > len(raw):
            raise ValueError('WAD directory extends past end of file')

        for i in range(numlumps):
            ofs = dirofs + i * _LUMP_SIZE
            filepos, size, raw_name = struct.unpack_from(_LUMP_FMT, raw, ofs)

            # Null-terminate and uppercase the name
            try:
                end = raw_name.index(0)
                raw_name = raw_name[:end]
            except ValueError:
                pass
            name = raw_name.decode('ascii', errors='replace').upper()

            # Grab lump data (marker lumps have size 0)
            data = raw[filepos: filepos + size] if size > 0 else b''
            lump = Lump(name, data)
            self._lumps.append(lump)

            if name not in self._index:
                self._index[name] = []
            self._index[name].append(i)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_lump(self, name: str) -> Lump:
        """Return the last lump with this name (PWAD override semantics)."""
        name = name.upper()
        indices = self._index.get(name)
        if not indices:
            raise KeyError(f'Lump not found: {name}')
        return self._lumps[indices[-1]]

    def get_lump_data(self, name: str) -> bytes:
        return self.get_lump(name).data

    def has_lump(self, name: str) -> bool:
        return name.upper() in self._index

    def get_lump_index(self, name: str) -> int:
        """Index of the last lump with this name in the directory."""
        name = name.upper()
        indices = self._index.get(name)
        if not indices:
            raise KeyError(f'Lump not found: {name}')
        return indices[-1]

    def get_lump_by_index(self, idx: int) -> Lump:
        return self._lumps[idx]

    # ------------------------------------------------------------------
    # Map lumps
    # ------------------------------------------------------------------
    # Map names: E1M1..E3M9 (Doom 1) or MAP01..MAP32 (Doom 2)
    _MAP_LUMP_COUNT = 11   # label + ML_THINGS..ML_BLOCKMAP

    def get_map_lumps(self, map_name: str) -> list:
        """
        Return the 11 lumps for a map (ML_LABEL..ML_BLOCKMAP) as a list
        indexed by the ML_* constants in doomdef.py.
        """
        map_name = map_name.upper()
        start = self.get_lump_index(map_name)
        end   = start + self._MAP_LUMP_COUNT

        if end > len(self._lumps):
            raise ValueError(f'Map {map_name}: not enough lumps after marker')

        return self._lumps[start: end]

    # ------------------------------------------------------------------
    # Sprite / flat / texture namespace helpers
    # ------------------------------------------------------------------
    def lumps_between(self, start_marker: str, end_marker: str) -> list:
        """
        Return all lumps strictly between two marker lumps.
        e.g. lumps_between('S_START', 'S_END') → sprite lumps
        """
        start_marker = start_marker.upper()
        end_marker   = end_marker.upper()

        in_range = False
        result   = []
        for lump in self._lumps:
            if lump.name == start_marker:
                in_range = True
                continue
            if lump.name == end_marker:
                break
            if in_range and lump.data:
                result.append(lump)
        return result

    def get_sprite_lumps(self) -> list:
        lumps = self.lumps_between('S_START', 'S_END')
        if not lumps:
            lumps = self.lumps_between('SS_START', 'SS_END')
        return lumps

    def get_flat_lumps(self) -> list:
        return self.lumps_between('F_START', 'F_END')

    # ------------------------------------------------------------------
    # Iteration / debug
    # ------------------------------------------------------------------
    def __len__(self):
        return len(self._lumps)

    def __iter__(self):
        return iter(self._lumps)

    def __repr__(self):
        kind = 'IWAD' if self.iwad else 'PWAD'
        return f'WAD({kind}, {len(self._lumps)} lumps, {self.path!r})'

    def list_lumps(self) -> list:
        """Return all lump names in directory order."""
        return [l.name for l in self._lumps]


# ------------------------------------------------------------------
# Module-level singleton — set by main startup
# ------------------------------------------------------------------
_wad: WAD | None = None

def load_wad(path: str) -> WAD:
    global _wad
    _wad = WAD(path)
    return _wad

def get_wad() -> WAD:
    if _wad is None:
        raise RuntimeError('WAD not loaded — call load_wad() first')
    return _wad
