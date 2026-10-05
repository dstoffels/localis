---
name: Bug report
about: Something doesn't work as documented, including search results that miss or
  rank poorly
title: 'Bug: '
labels: bug
assignees: dstoffels
type: Bug

---

<!-- A wrong or missing record is a data issue; use "Wrong or missing data" instead. -->

### What happened
<!-- For a search problem: the exact query, and the results with their scores, e.g. `print(localis.cities.search("Springfeld, Illinois"))`. Scores show whether the right record ranked too low or never came back. -->


### What you expected
<!-- For a search problem: the record you expected, by its key (`5128581`, `US-CA`) if you know it. -->


### Reproduction
<!-- The smallest code that shows it. -->

```python
import localis

```

### Traceback
<!-- If it raised, the full traceback. -->

```

```

### Settings
<!-- Any registry settings in effect: `cities.set_population_threshold(...)`, `countries.set_include_historic(...)`, a non-default `limit`. -->


### Versions
<!-- `python -c "import localis, sys; print(localis.__version__, sys.version)"`, plus your OS. -->


### Anything else
