import type { WorkoutCard } from './types';

export async function generatePDF(card: WorkoutCard): Promise<void> {
  const { jsPDF } = await import('jspdf');
  const doc = new jsPDF();
  let y = 20;

  doc.setFontSize(22);
  doc.setFont('helvetica', 'bold');
  doc.text(card.content.title, 20, y);
  y += 10;

  doc.setFontSize(11);
  doc.setFont('helvetica', 'normal');
  doc.text(card.content.description, 20, y, { maxWidth: 170 });
  y += 15;

  for (const day of card.content.days) {
    if (y > 260) { doc.addPage(); y = 20; }
    doc.setFontSize(13);
    doc.setFont('helvetica', 'bold');
    doc.text(`${day.day} — ${day.label}`, 20, y);
    y += 8;

    for (const ex of day.exercises) {
      if (y > 270) { doc.addPage(); y = 20; }
      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      doc.text(`• ${ex.name}  ${ex.sets}×${ex.reps}  rest: ${ex.rest}`, 25, y);
      y += 6;
      if (ex.notes) {
        doc.setTextColor(120, 120, 120);
        doc.text(`  ${ex.notes}`, 25, y);
        doc.setTextColor(0, 0, 0);
        y += 5;
      }
    }
    y += 5;
  }

  doc.save(`${card.content.title.replace(/\s+/g, '_')}.pdf`);
}
