from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import GradingEvent
from .permissions import EventPermission
from .serializers import GradingEventSerializer


class GradingEventViewSet(viewsets.ViewSet):
    permission_classes = [EventPermission]

    def get_queryset(self):
        farm_id = self.kwargs.get("farm_pk")
        return GradingEvent.objects.filter(
            cycle__farm_id=farm_id
        ).select_related("cycle", "source_pond_batch", "to_pond_batch").order_by("-date")

    def create(self, request, farm_id=None):
        serializer = GradingEventSerializer(
            data=request.data,
            context={"request": request, "farm_id": farm_id},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, farm_id=None):
        queryset = self.get_queryset()
        serializer = GradingEventSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, farm_id=None):
        event = self.get_queryset().get(pk=pk)
        serializer = GradingEventSerializer(event)
        return Response(serializer.data)
