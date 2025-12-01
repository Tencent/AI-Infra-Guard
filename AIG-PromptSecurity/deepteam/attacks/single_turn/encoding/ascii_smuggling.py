from deepteam.attacks import BaseAttack
import random

class AsciiSmuggling(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        enhancement_methods = [
            self.tag_char_smuggling,
            self.variant_smuggling,
            self.sneaky_bits_smuggling
        ]
        method = random.choice(enhancement_methods)
        return method(attack)

    def tag_char_smuggling(self, payload: str, desired_emoji: str = "😈"):
        """
        Use Unicode tags to smuggle ASCII characters.
        For tag char smuggling to work, it must be appended to an emoji, per the Unicode spec.
        https://unicode.org/reports/tr51/

        Args:
            payload (str): The payload we wish to hide.
            desired_emoji (str): Must be an emoji per unicode spec. Defaults to 😈

        Returns:
            desired_emoji + encoded payload (str): Payload encoded in unicode tags attached to the emoji.
        """
        encoded_payload = "".join(chr(0xE0000 + ord(ch)) for ch in payload)
        return desired_emoji + encoded_payload

    def variant_smuggling(self, payload: str):
        """
        Use Unicode variant selectors and supplement to smuggle ASCII characters.
        Unlike tag chars, variant selectors do not need to be appended to an emoji and there is no limit to the number of
        variant selectors that can be concatenated together, according to the unicode spec.
        https://www.unicode.org/versions/Unicode16.0.0/

        Args:
            payload (str): Payload to be encoded

        Returns:
            encoded_payload (str): The payload encoded in variant selectors.
        """
        encoded_payload = "".join(chr(0xE0100 + ord(ch)) for ch in payload)
        return encoded_payload

    def sneaky_bits_smuggling(self, payload: str):
        """
        Use Sneaky Bits as described by Johann Rehberger in
        https://embracethered.com/blog/posts/2025/sneaky-bits-and-ascii-smuggler/ to encode
        ASCII characters using invisible times (U+2062) and invisible plus (U+2064) to encode 0 and 1.

        We replace spaces with zero-width space (U+200B).

        Args:
            payload (str): Payload to be encoded

        Returns:
            encoded_payload (str): Payload encoded as binary, joined by zero-width spaces.
        """
        char_map = {"0": chr(0x2062), "1": chr(0x2064)}
        encoded_payload = list()
        for ch in payload:
            if ord(ch) == 0x20:
                encoded_payload.append(chr(0x200B))
            else:
                for rep in bin(ord(ch)).removeprefix("0b"):
                    encoded_payload.append(char_map[rep])
        return "".join(encoded_payload)