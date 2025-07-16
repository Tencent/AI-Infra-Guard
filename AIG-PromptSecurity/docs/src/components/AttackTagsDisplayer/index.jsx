import React from "react";
import styles from "./AttackTagsDisplayer.module.css";

const AttackTagsDisplayer = ({ multiTurn=false, singleTurn=false, encodingBased=false, llmSimulated=false, custom=false }) => {
  return (
    <div className={styles.tagsDisplayer}>
      {multiTurn && <div className={`${styles.pill} ${styles.multiTurn}`}>Multi-turn</div>}
      {singleTurn && <div className={`${styles.pill} ${styles.singleTurn}`}>Single-turn</div>}
      {encodingBased && <div className={`${styles.pill} ${styles.encodingBased}`}>Encoding-based</div>}
      {llmSimulated && <div className={`${styles.pill} ${styles.llmSimulated}`}>LLM-simulated</div>}
      {custom && <div className={`${styles.pill} ${styles.custom}`}>Custom</div>}
    </div>
  );
};

export default AttackTagsDisplayer;
