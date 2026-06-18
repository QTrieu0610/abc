import { apiRequest, buildQuery } from "./client";

export interface CrawlJobRecord {
  job_name?: string;
  target_site?: string;
  profile?: string;
  status?: string;
  source_status?: string;
  progress?: number;
  records?: number;
  topic?: string;
  source?: string;
  last_run?: string;
  message?: string;
}

export interface CrawlJobsResponse {
  timestamp?: string;
  count?: number;
  jobs?: CrawlJobRecord[];
}

export function getCrawlJobs(refresh = false) {
  return apiRequest<CrawlJobsResponse>(`/api/crawl-jobs${buildQuery({ refresh })}`);
}
