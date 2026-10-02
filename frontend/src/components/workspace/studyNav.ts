export type StudyParams = {
  method: string;
  name: string;
  lang: string;
  project: string;
  participants?: number;
};

/**
 * The query a study carries between the builder, recruit, publish and preview
 * screens. Returned as params rather than a pre-encoded string so it can be
 * handed to `withQuery`, which owns URL encoding and drops empty values — a
 * study that has not been named yet must not travel as `name=`.
 */
export function studyQuery(params: StudyParams): Record<string, string | number | undefined> {
  const query: Record<string, string | number | undefined> = {
    method: params.method,
    name: params.name,
    lang: params.lang,
    project: params.project,
  };
  if (typeof params.participants === "number") query.participants = params.participants;
  return query;
}
