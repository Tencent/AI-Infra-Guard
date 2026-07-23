/**
 * Fix DOM conflicts between React and third-party page translation extensions
 * such as Chrome / Google Translate.
 *
 * Background:
 * Translation extensions replace text nodes (TextNode), causing React during
 * the commit phase to call `parent.insertBefore(child, before)` or
 * `parent.removeChild(child)` while the child has already been moved away
 * by the translation extension, which throws:
 *   NotFoundError: Failed to execute 'insertBefore' on 'Node': The node
 *   before which the new node is to be inserted is not a child of this node.
 *
 * Solution (a common community patch): when the parent of the node that
 * React is operating on does not match the expected one, degrade gracefully
 * instead of throwing to avoid crashing the whole app.
 *
 * Reference: facebook/react#11538
 */
export function applyTranslateDomFix(): void {
  if (typeof Node === 'undefined' || !Node.prototype) return;

  const proto = Node.prototype as Node & {
    __translateDomFixApplied?: boolean;
  };
  if (proto.__translateDomFixApplied) return;
  proto.__translateDomFixApplied = true;

  const originalRemoveChild = Node.prototype.removeChild;
  Node.prototype.removeChild = function <T extends Node>(child: T): T {
    if (child.parentNode !== this) {
      if (child.parentNode) {
        // The node has been moved by the translation extension; remove it from its real parent
        return originalRemoveChild.call(child.parentNode, child) as T;
      }
      // Already detached from the DOM; return directly to avoid crashing
      return child;
    }
    return originalRemoveChild.call(this, child) as T;
  } as typeof Node.prototype.removeChild;

  const originalInsertBefore = Node.prototype.insertBefore;
  Node.prototype.insertBefore = function <T extends Node>(
    newNode: T,
    referenceNode: Node | null,
  ): T {
    if (referenceNode && referenceNode.parentNode !== this) {
      // The reference node has been moved by the translation extension; fall back to appendChild to avoid throwing
      return this.appendChild(newNode) as unknown as T;
    }
    return originalInsertBefore.call(this, newNode, referenceNode) as T;
  } as typeof Node.prototype.insertBefore;
}
