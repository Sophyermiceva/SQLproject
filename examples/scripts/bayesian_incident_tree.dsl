LOAD bayes_incident_events;
LOAD bayes_incident_conditionals;

NODE Event KEY event_id NAME name PRIOR prior FROM bayes_incident_events;

EDGE Causes
    FROM bayes_incident_conditionals
    SOURCE parent_event
    TARGET child_event
    PROBABILITY probability
    GIVEN parent_state;
