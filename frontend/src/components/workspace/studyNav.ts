export type StudyParams = {
  method: string;
  name: string;
  lang: string;
  project: string;
  participants?: number;
};

export function studyQuery(params: StudyParams) {
  const qs = new URLSearchParams({
    method: params.method,
    name: params.name,
    lang: params.lang,
    project: params.project,
  });
  if (typeof params.participants === "number") qs.set("participants", String(params.participants));
  return qs.toString();
}
