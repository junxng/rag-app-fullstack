import styles from '../styles/layout.module.css'

export default function Layout({ children }) {
  return (
    <div className={styles.layout}>
      <h1 className={styles.title}>Retrieval-Augmented Generation (RAG) Application</h1>
      <p className={styles.subtitle}>By dungnq49@fpt.com</p>
      <main>{children}</main>
    </div>
  )
}