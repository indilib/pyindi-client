%module(directors="1") PyIndi
%{
#include <indibase.h>
#include <indiapi.h>
#include <baseclient.h>
#include <basedevice.h>


#include <indiproperty.h>
#include <indiproperties.h>

#include <indipropertybasic.h>
#include <indipropertytext.h>
#include <indipropertynumber.h>
#include <indipropertyswitch.h>
#include <indipropertylight.h>
#include <indipropertyblob.h>

#include <stdexcept>
%}

%include "std_vector.i"
%include "std_except.i"
%include "std_string.i"
%include "stdint.i"

%feature("director") BaseClient;
%feature("director:except") {
    if( $error != NULL ) {
        PyObject *ptype, *pvalue, *ptraceback;
        PyErr_Fetch( &ptype, &pvalue, &ptraceback );
        PyErr_Restore( ptype, pvalue, ptraceback );
        PyErr_Print();
        Py_Exit(1);
    }
} 

%template(BaseDeviceVector) std::vector<INDI::BaseDevice *>;
%template(PropertyVector) std::vector<INDI::Property *>;

%include <indimacros.h>
%include <indibasetypes.h>
%include <indibase.h>
%include <indiapi.h>
%include <baseclient.h>
%include <basedevice.h>
%include <indiwidgettraits.h>

// INDI::PropertyView (low-level decorator for IXXXPropertyView)
// INDI::WidgetView (low-level decorator for IXXX)
%ignore INDI::PropertyView::apply;
%ignore INDI::PropertyView::define;
%ignore INDI::PropertyView::vapply;
%ignore INDI::PropertyView::vdefine;

%include <indipropertyview.h>

%exception {
    try {
        $action
    } catch (std::out_of_range &e) {
      SWIG_exception(SWIG_IndexError, "Index out of bounds");
    }
}
%extend INDI::PropertyView {
  const INDI::WidgetView<T> * __getitem__(int index) {
    if (index >= $self->count()) {
      throw std::out_of_range("Index out of bounds");
    }
    return $self->at(index);
  }

  int __len__() {
    return $self->count();
  }
}

%template(PropertyViewText)   INDI::PropertyView<IText>;
%template(PropertyViewNumber) INDI::PropertyView<INumber>;
%template(PropertyViewSwitch) INDI::PropertyView<ISwitch>;
%template(PropertyViewLight)  INDI::PropertyView<ILight>;
%template(PropertyViewBlob)   INDI::PropertyView<IBLOB>;

%template(WidgetViewText)     INDI::WidgetView<IText>;
%template(WidgetViewNumber)   INDI::WidgetView<INumber>;
%template(WidgetViewSwitch)   INDI::WidgetView<ISwitch>;
%template(WidgetViewLight)    INDI::WidgetView<ILight>;
%template(WidgetViewBlob)     INDI::WidgetView<IBLOB>;

// INDI::Property - generic container for INDI properties
%ignore INDI::Property::apply;
%ignore INDI::Property::define;
%ignore INDI::Property::vapply;
%ignore INDI::Property::vdefine;

%include <indiproperty.h>

// INDI::Property Typed -typed container for INDI properties
%ignore INDI::PropertyBasic::apply;
%ignore INDI::PropertyBasic::define;
%ignore INDI::PropertyBasic::vapply;
%ignore INDI::PropertyBasic::vdefine;

%include <indipropertybasic.h>

%extend INDI::PropertyBasic {
  const INDI::WidgetView<T> * __getitem__(int index) {
    return $self->at(index);
  }

  int __len__() {
    return $self->size();
  }
}

%template(PropertyBasicText)   INDI::PropertyBasic<IText>;
%template(PropertyBasicNumber) INDI::PropertyBasic<INumber>;
%template(PropertyBasicSwitch) INDI::PropertyBasic<ISwitch>;
%template(PropertyBasicLight)  INDI::PropertyBasic<ILight>;
%template(PropertyBasicBlob)   INDI::PropertyBasic<IBLOB>;

%include <indipropertytext.h>
%include <indipropertynumber.h>
%include <indipropertyswitch.h>
%include <indipropertylight.h>
%include <indipropertyblob.h>

typedef enum {
B_NEVER=0,
B_ALSO,
B_ONLY
} BLOBHandling;

%extend _ITextVectorProperty {
  IText *__getitem__(int index) throw(std::out_of_range) {
    if (index >= $self->ntp) throw std::out_of_range("VectorProperty index out of bounds");
    return $self->tp + index;
  }
  int __len__() {
    return $self->ntp;
  }
 };
%extend _INumberVectorProperty {
  INumber *__getitem__(int index) throw(std::out_of_range) {
    if (index >= $self->nnp) throw std::out_of_range("VectorProperty index out of bounds");
    return $self->np + index;
  }
  int __len__() {
    return $self->nnp;
  }
 };
%extend _ISwitchVectorProperty {
  ISwitch *__getitem__(int index) throw(std::out_of_range) {
    if (index >= $self->nsp) throw std::out_of_range("VectorProperty index out of bounds");
    return $self->sp + index;
  }
  int __len__() {
    return $self->nsp;
  }
 };
%extend _ILightVectorProperty {
  ILight *__getitem__(int index) throw(std::out_of_range) {
    if (index >= $self->nlp) throw std::out_of_range("VectorProperty index out of bounds");
    return $self->lp + index;
  }
  int __len__() {
    return $self->nlp;
  }
 };
%extend _IBLOBVectorProperty {
  IBLOB *__getitem__(int index) throw(std::out_of_range) {
    if (index >= $self->nbp) throw std::out_of_range("VectorProperty index out of bounds");
    return $self->bp + index;
  }
  int __len__() {
    return $self->nbp;
  }
 };


%extend IBLOB {
  PyObject *getblobdata() {
    PyObject *result;

    result = PyByteArray_FromStringAndSize((const char*) $self->blob, $self->size);
    return result;
  }
 };


%ignore INDI::Properties::at;
%ignore INDI::Properties::front;
%ignore INDI::Properties::back;
%ignore INDI::Properties::empty;

%include <indiproperties.h>

%extend INDI::Properties {
  INDI::Property * __getitem__(int index) {
    if ((unsigned int)index >= $self->size()) throw std::out_of_range("Properties index out of bounds");
    return &($self->at(index));
  }

  int __len__() {
    return $self->size();
  }
}


%extend INDI::BaseClient {
  %typemap(in) (char *data, long len) {
    $1 = PyBytes_AsString($input);
    $2 = PyBytes_Size($input);
  }


  public:
    void sendOneBlobFromBuffer(const char *name, const char *type, char *data, long len) {
      $self->sendOneBlob(name, len, type, (void*)(data));
    }
    /* TODO(chripell): is there a way to use %implicitconv? */
    void sendNewText(INDI::PropertyView<IText> * pp) {
      $self->sendNewText(static_cast<ITextVectorProperty *>(pp));
    }
    void sendNewNumber(INDI::PropertyView<INumber> * pp) {
      $self->sendNewNumber(static_cast<INumberVectorProperty *>(pp));
    }
    void sendNewSwitch(INDI::PropertyView<ISwitch> * pp) {
      $self->sendNewSwitch(static_cast<ISwitchVectorProperty *>(pp));
    }
}
