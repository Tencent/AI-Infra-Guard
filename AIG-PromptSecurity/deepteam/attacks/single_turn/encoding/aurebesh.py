from deepteam.attacks import BaseAttack

class Aurebesh(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight
        self.map = {
            'a': 'Aurek', 'b': 'Besh', 'c': 'Cresh', 'd': 'Dorn', 'e': 'Esk', 'f': 'Forn', 'g': 'Grek', 'h': 'Herf', 'i': 'Isk',
            'j': 'Jenth', 'k': 'Krill', 'l': 'Leth', 'm': 'Mern', 'n': 'Nern', 'o': 'Osk', 'p': 'Peth', 'q': 'Qek', 'r': 'Resh',
            's': 'Senth', 't': 'Trill', 'u': 'Usk', 'v': 'Vev', 'w': 'Wesk', 'x': 'Xesh', 'y': 'Yirt', 'z': 'Zerek',
            'A': 'AUREK', 'B': 'BESH', 'C': 'CRESH', 'D': 'DORN', 'E': 'ESK', 'F': 'FORN', 'G': 'GREK', 'H': 'HERF', 'I': 'ISK',
            'J': 'JENTH', 'K': 'KRILL', 'L': 'LETH', 'M': 'MERN', 'N': 'NERN', 'O': 'OSK', 'P': 'PETH', 'Q': 'QEK', 'R': 'RESH',
            'S': 'SENTH', 'T': 'TRILL', 'U': 'USK', 'V': 'VEV', 'W': 'WESK', 'X': 'XESH', 'Y': 'YIRT', 'Z': 'ZEREK'
        }

    def enhance(self, attack: str) -> str:
        result = []
        for c in attack:
            if c.lower() in self.map:
                result.append(self.map.get(c, self.map[c.lower()]))
            else:
                result.append(c)
        return ' '.join(result)
