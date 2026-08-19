# BaseETL Migration Guide

**Purpose**: Migrate existing ETLs to type-safe refactored BaseETL
**Audience**: Developers maintaining ETL processes
**Time Required**: 30-60 minutes per ETL
**Status**: Ready for Migration

---

## Overview

The refactored `BaseETL` fixes all type safety issues and provides a more robust, type-safe foundation for ETL processes. This guide shows you how to migrate existing ETLs to use the new type-safe version.

## Key Changes

### 1. Constrained Type Variables

**Before** (Unconstrained generics):
```python
# ❌ BAD: No type constraints
InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")

class BaseETL(ABC, Generic[InputType, OutputType]):
    def transform(self, data: list[InputType]) -> list[OutputType]:
        # What types are these? No constraints.
        pass
```

**After** (Properly constrained):
```python
# ✅ GOOD: Type-safe with protocol and bounds
@runtime_checkable
class Transformable(Protocol):
    """Protocol for data that can be transformed."""
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Transformable: ...

InputType = TypeVar("InputType", bound=Transformable)
OutputType = TypeVar("OutputType", bound=TimestampedModel)

class BaseETL(ABC, Generic[InputType, OutputType]):
    def transform(self, data: list[InputType]) -> list[OutputType]:
        # Type-safe: InputType must be Transformable
        # Type-safe: OutputType must be TimestampedModel
        pass
```

### 2. Type-Safe Serialization

**Before** (Mixed types):
```python
# ❌ BAD: Can't guarantee serialization works
def load(self, data: list[OutputType]) -> None:
    serializable_data = [item.dict() for item in data]  # May fail
```

**After** (Type-safe):
```python
# ✅ GOOD: Handles both model_dump() and dict() methods
def _serialize_to_dict(self, item: OutputType) -> dict[str, Any]:
    """Serialize TimestampedModel to dictionary."""
    if hasattr(item, "model_dump"):
        return item.model_dump(mode="json")
    elif hasattr(item, "dict"):
        return item.dict()
    else:
        return dict(item)
```

### 3. Proper Path Handling

**Before** (Potential None):
```python
# ❌ BAD: project_root could be None
self.data_dir = Path(self.settings.project_root) / "data" / name
```

**After** (Type-safe):
```python
# ✅ GOOD: Validate project_root exists
project_root = self.settings.project_root
if not project_root:
    raise ValueError("settings.project_root cannot be None or empty")

self.data_dir = Path(project_root) / "data" / name
```

---

## Migration Steps

### Step 1: Review Your Current ETL

Identify which pattern your ETL follows:

**Pattern A: Simple dict-to-dict ETL**
```python
class MyETL(BaseETL[dict, dict]):
    def extract(self) -> list[dict[str, Any]]:
        # Returns list of dicts
        pass

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Returns list of dicts
        pass

    def load(self, data: list[dict[str, Any]]) -> None:
        # Loads dicts
        pass
```

**Pattern B: Model-based ETL (TimestampedModel)**
```python
class MyETL(BaseETL[dict, MyModel]):
    def extract(self) -> list[dict[str, Any]]:
        # Returns list of dicts
        pass

    def transform(self, data: list[dict[str, Any]]) -> list[MyModel]:
        # Returns list of MyModel instances
        pass

    def load(self, data: list[MyModel]) -> None:
        # Loads MyModel instances
        pass
```

**Pattern C: DataFrame ETL**
```python
class MyETL(DataFrameETL[dict, MyModel]):
    def extract_to_dataframe(self) -> pd.DataFrame:
        # Returns DataFrame
        pass

    def transform_dataframe(self, df: pd.DataFrame) -> list[MyModel]:
        # Returns list of MyModel instances
        pass
```

### Step 2: Update Imports

**Before**:
```python
from src.etl.base import BaseETL, SimpleETL, DataFrameETL
```

**After**:
```python
from src.etl.base_refactored import (
    BaseETL,
    SimpleETL,
    DataFrameETL,
    Transformable,  # New: Protocol for input types
)
```

### Step 3: Ensure Input Type Conforms to Transformable

If your ETL uses custom input types, ensure they implement the `Transformable` protocol:

**Before** (May not conform):
```python
class RawData:
    def __init__(self, data: dict):
        self.data = data

class MyETL(BaseETL[RawData, MyModel]):
    def extract(self) -> list[RawData]:
        pass
```

**After** (Implements Transformable):
```python
@dataclass
class RawData:
    """Raw data that conforms to Transformable protocol."""
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RawData:
        """Create from dictionary."""
        return cls(data)
```

### Step 4: Update Transform Method

If your ETL returns non-TimestampedModel types, update to use TimestampedModel:

**Before** (Returns dicts):
```python
class MyETL(BaseETL[dict, dict]):
    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Transforms dicts to dicts
        return data
```

**After** (Returns TimestampedModel):
```python
from src.models.base import TimestampedModel
from pydantic import BaseModel

class MyOutputModel(TimestampedModel):
    """Output model inheriting from TimestampedModel."""
    title: str
    url: str
    # ... other fields

class MyETL(BaseETL[dict, MyOutputModel]):
    def transform(self, data: list[dict[str, Any]]) -> list[MyOutputModel]:
        # Transforms dicts to MyOutputModel instances
        return [MyOutputModel(**item) for item in data]
```

### Step 5: Test the Migrated ETL

Run your ETL and verify it works correctly:

```bash
# Run single ETL
uv run python src/etl/myfolder/my_etl.py

# Run all ETLs
./run_all_etl.sh  # Linux/Mac
.\run_all_etl.bat  # Windows

# Check logs
tail -f logs/etl.log
```

---

## Example Migrations

### Example 1: Simple ArXiv ETL

**Before** (`src/etl/arxiv/arxiv_etl.py`):
```python
from src.etl.base import BaseETL
from src.models.base import TimestampedModel

class ArxivPaperModel(TimestampedModel):
    title: str
    url: str
    # ...

class ArxivETL(BaseETL[dict, ArxivPaperModel]):
    def extract(self) -> list[dict[str, Any]]:
        # Extract papers from API/RSS
        return papers

    def transform(self, data: list[dict[str, Any]]) -> list[ArxivPaperModel]:
        # Transform to models
        return [ArxivPaperModel(**paper) for paper in data]

    def load(self, data: list[ArxivPaperModel]) -> None:
        # Load to file
        pass
```

**After** (No changes needed!):
```python
from src.etl.base_refactored import BaseETL  # ✅ Just update import
from src.models.base import TimestampedModel

class ArxivPaperModel(TimestampedModel):
    title: str
    url: str
    # ...

class ArxivETL(BaseETL[dict, ArxivPaperModel]):
    # ✅ No changes needed - already type-safe!
    def extract(self) -> list[dict[str, Any]]:
        return papers

    def transform(self, data: list[dict[str, Any]]) -> list[ArxivPaperModel]:
        return [ArxivPaperModel(**paper) for paper in data]

    def load(self, data: list[ArxivPaperModel]) -> None:
        pass
```

### Example 2: Custom Input Type ETL

**Before** (Non-conforming input type):
```python
from src.etl.base import BaseETL

class RawCourse:
    def __init__(self, title: str, url: str):
        self.title = title
        self.url = url

class CourseETL(BaseETL[RawCourse, CourseModel]):
    def extract(self) -> list[RawCourse]:
        pass

    def transform(self, data: list[RawCourse]) -> list[CourseModel]:
        # Manual conversion
        return [
            CourseModel(
                title=item.title,
                url=item.url,
            )
            for item in data
        ]
```

**After** (Implements Transformable protocol):
```python
from src.etl.base_refactored import BaseETL, Transformable
from dataclasses import dataclass

@dataclass
class RawCourse(Transformable):
    """Raw course data conforming to Transformable protocol."""
    title: str
    url: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {"title": self.title, "url": self.url}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RawCourse:
        """Create from dictionary."""
        return cls(title=data["title"], url=data["url"])

class CourseETL(BaseETL[RawCourse, CourseModel]):
    # ✅ Now type-safe: RawCourse conforms to Transformable
    def extract(self) -> list[RawCourse]:
        pass

    def transform(self, data: list[RawCourse]) -> list[CourseModel]:
        return [
            CourseModel(
                title=item.title,
                url=item.url,
            )
            for item in data
        ]
```

### Example 3: DataFrame ETL

**Before** (Old base):
```python
from src.etl.base import DataFrameETL

class GamesETL(DataFrameETL[dict, GameModel]):
    def extract_to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([...])

    def transform_dataframe(self, df: pd.DataFrame) -> list[GameModel]:
        return [GameModel(**row) for row in df.to_dict("records")]
```

**After** (Refactored base):
```python
from src.etl.base_refactored import DataFrameETL  # ✅ Just update import

class GamesETL(DataFrameETL[dict, GameModel]):
    # ✅ No changes needed - compatible!
    def extract_to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([...])

    def transform_dataframe(self, df: pd.DataFrame) -> list[GameModel]:
        return [GameModel(**row) for row in df.to_dict("records")]
```

---

## Type Safety Benefits

### Before Migration (Type Issues)
```
❌ InputType/OutputType unconstrained
❌ Runtime errors from type mismatches
❌ No IDE autocomplete support
❌ MyPy errors in base.py
❌ Hard to refactor safely
```

### After Migration (Type Safe)
```
✅ InputType must conform to Transformable
✅ OutputType must inherit from TimestampedModel
✅ Compile-time type checking
✅ Full IDE autocomplete support
✅ MyPy clean (0 errors)
✅ Safe refactoring with type guarantees
```

---

## Checklist for Each ETL

- [ ] **Review current ETL implementation**
- [ ] **Identify pattern** (Simple, Model-based, DataFrame)
- [ ] **Update imports** to use `base_refactored`
- [ ] **Ensure input type conforms to Transformable** (if custom type)
- [ ] **Ensure output type inherits from TimestampedModel** (if not already)
- [ ] **Test ETL execution** with `uv run python src/etl/...`
- [ ] **Verify output files** are generated correctly
- [ ] **Check logs** for errors or warnings
- [ ] **Run MyPy** to verify type safety: `uv run mypy src/etl/my_etl.py`

---

## Common Migration Issues

### Issue 1: "InputType does not conform to Transformable"

**Problem**: Your input type doesn't implement `to_dict()` and `from_dict()` methods.

**Solution**: Add these methods to your input type:

```python
class MyInputType:
    # Add these methods:
    def to_dict(self) -> dict[str, Any]:
        return self.__dict__

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MyInputType:
        return cls(**data)
```

### Issue 2: "OutputType is not a TimestampedModel"

**Problem**: Your output type doesn't inherit from `TimestampedModel`.

**Solution**: Update your output model to inherit from `TimestampedModel`:

```python
from src.models.base import TimestampedModel

class MyOutputModel(TimestampedModel):  # ✅ Add inheritance
    title: str
    url: str
    # ...
```

### Issue 3: "Path operation on None value"

**Problem**: `settings.project_root` is None.

**Solution**: The refactored base.py validates this for you. Just ensure your settings are configured correctly.

### Issue 4: "Serialization error in load()"

**Problem**: Custom serialization logic incompatible with new base.

**Solution**: Use the new `_serialize_to_dict()` helper method:

```python
def load(self, data: list[OutputType]) -> None:
    serializable_data = [self._serialize_to_dict(item) for item in data]
    # Save to file
```

---

## Testing Your Migration

### Unit Test Example

```python
import pytest
from src.etl.base_refactored import BaseETL
from src.models.base import TimestampedModel

class TestModel(TimestampedModel):
    title: str
    value: int

class TestETL(BaseETL[dict, TestModel]):
    def extract(self) -> list[dict[str, Any]]:
        return [{"title": "Test", "value": 42}]

    def transform(self, data: list[dict[str, Any]]) -> list[TestModel]:
        return [TestModel(**item) for item in data]

    def load(self, data: list[TestModel]) -> None:
        assert len(data) == 1
        assert data[0].title == "Test"

def test_etl_type_safety():
    """Test that ETL is type-safe."""
    etl = TestETL(name="test")
    metrics = etl.run()

    assert metrics.is_successful
    assert metrics.records_loaded == 1
```

### Integration Test Example

```bash
# Test specific ETL
uv run pytest Tests/etl/test_my_etl.py -v

# Test all ETLs
uv run pytest Tests/etl/ -v

# Type check specific ETL
uv run mypy src/etl/myfolder/my_etl.py

# Type check all ETLs
uv run mypy src/etl/
```

---

## Rollback Plan

If you encounter issues after migration:

1. **Revert import** to old base.py:
   ```python
   from src.etl.base import BaseETL  # Rollback
   ```

2. **Report issue** with:
   - ETL name
   - Error message
   - Stack trace
   - Input/output types

3. **Keep old base.py** until all ETLs are migrated and tested

---

## Timeline & Effort

| ETL Complexity | Time Required | Risk Level |
|----------------|---------------|------------|
| Simple (dict→dict) | 15-30 min | Low |
| Model-based | 30-45 min | Low |
| Custom input type | 45-60 min | Medium |
| DataFrame-based | 30-45 min | Low |

**Total Estimated Effort**: 2-4 hours for typical project (5-10 ETLs)

---

## Next Steps

1. **Start with simple ETLs** (dict→dict transformations)
2. **Migrate model-based ETLs** (already use TimestampedModel)
3. **Handle custom types** (add Transformable protocol)
4. **Test thoroughly** after each migration
5. **Update CI/CD** to use refactored base
6. **Deprecate old base.py** after all ETLs migrated

---

**Questions?** See `docs/REFACTORING_ANALYSIS.md` or `docs/REFACTORING_QUICKSTART.md`

**Report Issues**: GitHub issues with label "refactoring"
