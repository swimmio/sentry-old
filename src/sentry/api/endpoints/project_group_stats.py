from rest_framework.request import Request
from rest_framework.response import Response

from sentry.api.base import EnvironmentMixin, StatsMixin
from sentry.api.bases.project import ProjectEndpoint
from sentry.api.exceptions import ResourceDoesNotExist
from sentry.app import tsdb
from sentry.models import Environment, Group
from sentry.ratelimits.config import RateLimitConfig
from sentry.types.ratelimit import RateLimit, RateLimitCategory


class ProjectGroupStatsEndpoint(ProjectEndpoint, EnvironmentMixin, StatsMixin):
    enforce_rate_limit = True
    rate_limits = RateLimitConfig(
        group="issues",
        limit_overrides={
            "GET": {
                RateLimitCategory.IP: RateLimit(20, 1, 10),
                RateLimitCategory.USER: RateLimit(20, 1, 10),
                RateLimitCategory.ORGANIZATION: RateLimit(20, 1, 10),
            }
        },
    )

    def get(self, request: Request, project) -> Response:
        try:
            environment_id = self._get_environment_id_from_request(request, project.organization_id)
        except Environment.DoesNotExist:
            raise ResourceDoesNotExist

        group_ids = request.GET.getlist("id")
        if not group_ids:
            return Response(status=204)

        group_list = Group.objects.filter(project=project, id__in=group_ids)
        group_ids = [g.id for g in group_list]

        if not group_ids:
            return Response(status=204)

        data = tsdb.get_range(
            model=tsdb.models.group, keys=group_ids, **self._parse_args(request, environment_id)
        )

        return Response({str(k): v for k, v in data.items()})
