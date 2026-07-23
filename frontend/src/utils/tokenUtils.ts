/**
 * Mask the middle part of a token, producing a masked token of fixed length
 * @param token Original token
 * @param displayLength Total display length, defaults to 12
 * @param prefixLength Visible prefix length, defaults to 4
 * @param suffixLength Visible suffix length, defaults to 4
 * @returns Masked token string
 */
export const maskToken = (
  token: string,
  displayLength: number = 20,
  prefixLength: number = 4,
  suffixLength: number = 4,
): string => {
  if (!token || token.length === 0) {
    return '';
  }

  // If the token length is less than or equal to prefix + suffix, mask everything with '*'
  if (token.length <= prefixLength + suffixLength) {
    return '*'.repeat(Math.min(token.length, displayLength));
  }

  const prefix = token.substring(0, prefixLength);
  const suffix = token.substring(token.length - suffixLength);
  const middleLength = displayLength - prefixLength - suffixLength;
  const maskedMiddle = '*'.repeat(Math.max(middleLength, 4)); // At least 4 '*' characters

  return `${prefix}${maskedMiddle}${suffix}`;
};
