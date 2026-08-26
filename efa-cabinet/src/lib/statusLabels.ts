const STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  awaiting_docs: "Ждём регламенты",
  survey_open: "Идёт опрос сотрудников",
  processing: "Собираем архитектуру",
  done: "Готово"
};

export function statusLabel(status: string) {
  return STATUS_LABELS[status] || status;
}
