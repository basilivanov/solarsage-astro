// AI_HEADER
// module: M-WEB-READING
// wave: W-2.2
// purpose: Reading paragraphs display

interface ReadingProps {
  paragraphs: string[];
}

export function Reading({ paragraphs }: ReadingProps) {
  if (paragraphs.length === 0) return null;

  return (
    <section className="reading" data-testid="reading">
      {paragraphs.map((p, idx) => (
        <p key={idx} className="reading-paragraph">
          {p}
        </p>
      ))}
    </section>
  );
}
