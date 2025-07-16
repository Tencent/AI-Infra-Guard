import React from 'react';
import styles from './index.module.css';
import LayoutProvider from '@theme/Layout/Provider';
import Footer from '@theme/Footer';
import Link from '@docusaurus/Link';

class HomeNav extends React.Component {
    render() {
        return <div className={styles.homeNav}>
            <div><Link to={"/docs/getting-started"}>Docs</Link></div>
            <div><a href="https://github.com/confident-ai/deepteam" target="_blank">Github</a></div>
            <div><a href="https://confident-ai.com/blog" target="_blank">Blog</a></div>
            {/* <div><Link to="/guides/guides-rag-evaluation">Guides</Link></div> */}
            {/* <div className={styles.canHide}>
              <div><a href="https://github.com/confident-ai/deepteam" target="_blank">Github</a></div>
              <div><a href="https://confident-ai.com/blog" target="_blank">Blog</a></div>
            </div> */}
        </div>
    }
}

class ConfidentEnvelope extends React.Component {
  handleConfident = () => {
      window.open('https://confident-ai.com', '_blank');
  }

  render() {
    return <div className={styles.letterContainer} onClick={this.handleConfident}>
    <div className={styles.letterImage}>
      <div className={styles.animatedMail}>
        <div className={styles.backFold}></div>
        <div className={styles.letter}>
          <div className={styles.letterBorder}></div>
          <div className={styles.letterTitle}>Delivered by</div>
          <div className={styles.letterContentContainer}>
            <img src="icons/red-logo.svg" style={{width: "30px", height: "30px"}}/>
            <div className={styles.letterContext}>
              <span class="lexend-deca" style={{fontSize: "16px"}}>Confident AI</span>
            </div>
          </div>
          <div className={styles.letterStamp}>
            <div className={styles.letterStampInner}></div>
          </div>
        </div>
        <div className={styles.topFold}>
        </div>
        <div className={styles.body}></div>
        <div className={styles.leftFold}></div>
      </div>
      <div className={styles.shadow}></div>
    </div>
  </div>
  }
}

class FeatureCard extends React.Component {
  render() {
      const { title, link, description } = this.props;

      return (
          <Link to={link} className={styles.featureCard}>
            <div className={styles.featureCardContainer}>
              <span className={styles.title}>{title}<img src="icons/right-arrow.svg" /></span>
            </div>
            <p className={styles.description}>{description}</p>
          </Link>
      );
  }
}


class Index extends React.Component {
  handleConfident = () => {
      window.open('https://confident-ai.com', '_blank');
  }

    render() {
      return (
        <div className={styles.mainMainContainer}>
          <div className={styles.mainContainer}>
            <div className={styles.mainLeftContainer}>
              <img src="icons/DeepTeam.svg" />
              <div className={styles.contentContainer}>
                <h1>{`> the open-source LLM red teaming framework_`}</h1>
                <div className={styles.ctaContainer}>
                  <Link to={"/docs/getting-started"} className={styles.button}>Get Started</Link>
                  {/* <a href={"https://confident-ai.com"} className={styles.confidentLink}>
                    <span>Try the DeepTeam Platform</span>
                    <img className={styles.newTabIcon} src="icons/new-tab.svg"/>
                  </a> */}
                </div>
              </div>
            </div>
            <ConfidentEnvelope />
          </div>
          <div className={styles.featuresContainer}>
            <FeatureCard 
                title="Detect 40+ LLM Vulnerabilities"
                link="/docs/red-teaming-vulnerabilities" 
                description="Automatically scan for vulnerabilities such as bias, PII leakage, toxicity, etc."
            />
            <FeatureCard 
                title="SOTA Adersarial Attacks"
                link="/docs/red-teaming-adversarial-attacks" 
                description="Prompt injections, gray box, etc. to jailbreak your LLM"
            />
            <FeatureCard
                title="OWASP Top 10, NIST AI, etc." 
                link="/docs/red-teaming-owasp-top-10-for-llms" 
                description="OWASP Top 10 for LLMs, NIST AI, and so much more out of the box"
            />
          </div>
        </div>
      );
    }
  }



export default function (props) {
    return <LayoutProvider>
      <div className={styles.mainRapper}>
        <div className={styles.rapper}>
          <HomeNav />
          <Index {...props} />
        </div>
      </div>
        <Footer/>
    </LayoutProvider>;
};