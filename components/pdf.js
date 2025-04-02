import Image from 'next/image';
import styles from '../styles/pdf.module.css';

export default function PDFComponent(props) {
  const { pdf, onChange, onDelete } = props;
  return (
    <div className={styles.pdfRow}>
      <input
        className={styles.pdfCheckbox}
        name="selected"
        type="checkbox"
        checked={pdf.selected}
        onChange={(e) => onChange(e, pdf.id)}
      />
      <input
        className={styles.pdfInput}
        autoComplete="off"
        name="name"
        type="text"
        value={pdf.name}
        onChange={(e) => onChange(e, pdf.id)}
      />
      <a
        onClick={(e) => {
          e.preventDefault();
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/pdfs/${pdf.id}/presigned-url`)
            .then(res => res.json())
            .then(data => {
              // Open PDF in new tab with temporary URL
              window.open(data.url, '_blank');
            })
            .catch(err => {
              console.error("Error getting presigned URL:", err);
              // Fallback to original URL if error
              window.open(pdf.file, '_blank');
            });
        }}
        href="#"
        className={styles.viewPdfLink}
      >
        <Image src="/document-view.svg" width="22" height="22" />
      </a>
      <button
        className={styles.deleteBtn}
        onClick={() => onDelete(pdf.id)}
      >
        <Image src="/delete-outline.svg" width="24" height="24" />
      </button>
    </div>
  );
}
