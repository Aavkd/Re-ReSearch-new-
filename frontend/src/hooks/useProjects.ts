import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import {
  fetchProjects,
  createProject,
  fetchProjectSummary,
} from "../api/projects";
import type { AppNode, ProjectSummary } from "../types";

/** All project nodes — stale after 60 s. */
export function useProjectList() {
  return useQuery<AppNode[]>({
    queryKey: ["projects"],
    queryFn: fetchProjects,
    staleTime: 60_000,
  });
}

/** Mutation to create a new project.  Invalidates the `projects` list. */
export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation<AppNode, Error, string>({
    mutationFn: (name) => createProject(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

/**
 * Summary stats (node counts, recent artifacts) for a single project.
 * Only fetches when `id` is non-null / non-empty.
 */
export function useProjectSummary(id: string | null) {
  return useQuery<ProjectSummary>({
    queryKey: ["project", id],
    queryFn: () => fetchProjectSummary(id!),
    enabled: !!id,
  });
}
