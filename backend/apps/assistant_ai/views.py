from rest_framework.decorators import api_view,permission_classes,throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import SimpleRateThrottle
from .models import KnowledgeArticle
from .services import chat_answer

class ChatThrottle(SimpleRateThrottle):
    scope='sangam_ai_chat'
    def get_cache_key(self,request,view):
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {'scope':self.scope,'ident':request.user.pk}

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def knowledge(request):
    qs=KnowledgeArticle.objects.filter(is_published=True,audience__in=['ALL',request.user.role]).order_by('-updated_at')[:100]
    return Response([{'id':a.pk,'title':a.title,'content':a.content,'audience':a.audience} for a in qs])
