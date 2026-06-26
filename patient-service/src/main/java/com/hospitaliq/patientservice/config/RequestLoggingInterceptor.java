package com.hospitaliq.patientservice.config;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;
import org.springframework.web.servlet.ModelAndView;

/**
 * Logs every inbound HTTP request with authenticated user identity and response time.
 * Registered via {@link WebMvcConfig}.
 *
 * Example output:
 *   [REQUEST] GET /api/v1/patients | user=admin@hospital.com | 142ms | 200
 */
@Component
public class RequestLoggingInterceptor implements HandlerInterceptor {

    private static final Logger log = LoggerFactory.getLogger(RequestLoggingInterceptor.class);
    private static final String START_TIME_ATTR = "requestStartTime";

    @Override
    public boolean preHandle(HttpServletRequest request,
                             HttpServletResponse response,
                             Object handler) {
        request.setAttribute(START_TIME_ATTR, System.currentTimeMillis());
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request,
                                HttpServletResponse response,
                                Object handler,
                                Exception ex) {
        Long startTime = (Long) request.getAttribute(START_TIME_ATTR);
        long duration = startTime != null ? System.currentTimeMillis() - startTime : -1;

        String user = resolveUser();
        int status = response.getStatus();
        String method = request.getMethod();
        String uri = request.getRequestURI();

        String queryString = request.getQueryString();
        String fullUri = queryString != null ? uri + "?" + queryString : uri;

        if (ex != null) {
            log.error("[REQUEST] {} {} | user={} | {}ms | {} | error={}",
                    method, fullUri, user, duration, status, ex.getMessage());
        } else {
            log.info("[REQUEST] {} {} | user={} | {}ms | {}",
                    method, fullUri, user, duration, status);
        }
    }

    private String resolveUser() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.isAuthenticated() && auth.getPrincipal() instanceof String principal) {
            return principal;
        }
        return "anonymous";
    }
}
