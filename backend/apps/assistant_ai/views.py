from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view,permission_classes,throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import SimpleRateThrottle
from apps.accounts.permissions import IsIIC
from apps.mentoring.services import log
from .models import KnowledgeArticle
from .services import chat_answer

class ChatThrottle(SimpleRateThrottle):
    scope='sangam_ai_chat'
    def get_cache_key(self,request,view):
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {'scope':self.scope,'ident':request.user.pk}

@extend_schema(tags=['ai'], summary='Helpdesk chatbot grounded in published knowledge. Messages are never stored.',
               request=inline_serializer('ChatRequest', {'message': serializers.CharField(min_length=2, max_length=1000)}),
               responses=inline_serializer('ChatResponse', {'answer': serializers.CharField(), 'sources': serializers.ListField(),
                          'local_ai_used': serializers.BooleanField(), 'message_stored': serializers.BooleanField(),
                          'human_approval_required_for_matches': serializers.BooleanField()}))
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ChatThrottle])
def chat(request):
    question=request.data.get('message','')
    if not isinstance(question,str) or not 2 <= len(question.strip()) <= 1000:
        raise ValidationError({'message':'Message must be 2–1000 characters.'})
    # Deliberately NEVER save the question or answer in DB/audit logs.
    answer,sources,used_local_llm=chat_answer(question,request.user.role)
    return Response({'answer':answer,'sources':sources,'local_ai_used':used_local_llm,
                     'message_stored':False,'human_approval_required_for_matches':True})

@extend_schema(tags=['ai'], summary='Published knowledge articles for my role', responses=OpenApiTypes.OBJECT)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def knowledge(request):
    qs=KnowledgeArticle.objects.filter(is_published=True,audience__in=['ALL',request.user.role]).order_by('-updated_at')[:100]
    return Response([{'id':a.pk,'title':a.title,'content':a.content,'audience':a.audience} for a in qs])


class KnowledgeArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeArticle
        fields = ('id', 'title', 'content', 'audience', 'is_published', 'updated_at')
        read_only_fields = ('updated_at',)
    def validate_content(self, value):
        if len(value.strip()) < 20:
            raise serializers.ValidationError('Provide at least 20 characters of approved guidance.')
        return value


@extend_schema_view(**{action: extend_schema(tags=['ai'], summary=f'IIC: knowledge base ({action})')
                       for action in ('list', 'retrieve', 'create', 'update', 'partial_update', 'destroy')})
class KnowledgeAdminViewSet(viewsets.ModelViewSet):
    """IIC-managed, non-confidential guidance used to ground the chatbot."""
    serializer_class = KnowledgeArticleSerializer
    permission_classes = [IsIIC]
    queryset = KnowledgeArticle.objects.order_by('-updated_at')
    filterset_fields = ('audience', 'is_published')
    def perform_create(self, serializer):
        log(self.request.user, 'KNOWLEDGE_CREATED', serializer.save())
    def perform_update(self, serializer):
        log(self.request.user, 'KNOWLEDGE_UPDATED', serializer.save())
    def perform_destroy(self, instance):
        log(self.request.user, 'KNOWLEDGE_DELETED', instance)
        instance.delete()
