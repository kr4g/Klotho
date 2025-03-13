from enum import Enum, EnumMeta

__all__ = [
    'ANCIENT_GREEK',
    'RUNIC',
    'LOGOGRAPHIC',
    'CUNEIFORM',
    'MATHEMATICAL',
]

class DirectValueEnumMeta(EnumMeta):
    def __getattribute__(cls, name):
        member = super().__getattribute__(name)
        if isinstance(member, cls):
            return member.value
        return member

# ------------------------------------------------------------------------------------
# ANCIENT GREEK SYMBOLS
# ------------------------------------------------------------------------------------
class ANCIENT_GREEK(Enum, metaclass=DirectValueEnumMeta):
    '''
    Enum for Ancient Greek alphabet and symbols.
    
    
    '''
    class upper(Enum, metaclass=DirectValueEnumMeta):
        # Uppercase Greek Letters
        ALPHA_UPPER         = 'Α'
        BETA_UPPER          = 'Β'
        GAMMA_UPPER         = 'Γ'
        DELTA_UPPER         = 'Δ'
        EPSILON_UPPER       = 'Ε'
        ZETA_UPPER          = 'Ζ'
        ETA_UPPER           = 'Η'
        THETA_UPPER         = 'Θ'
        IOTA_UPPER          = 'Ι'
        KAPPA_UPPER         = 'Κ'
        LAMBDA_UPPER        = 'Λ'
        MU_UPPER            = 'Μ'
        NU_UPPER            = 'Ν'
        XI_UPPER            = 'Ξ'
        OMICRON_UPPER       = 'Ο'
        PI_UPPER            = 'Π'
        RHO_UPPER           = 'Ρ'
        SIGMA_UPPER         = 'Σ'
        TAU_UPPER           = 'Τ'
        UPSILON_UPPER       = 'Υ'
        PHI_UPPER           = 'Φ'
        CHI_UPPER           = 'Χ'
        PSI_UPPER           = 'Ψ'
        OMEGA_UPPER         = 'Ω'

    class lower(Enum, metaclass=DirectValueEnumMeta):
        # Lowercase Greek Letters
        ALPHA_LOWER         = 'α'
        BETA_LOWER          = 'β'
        GAMMA_LOWER         = 'γ'
        DELTA_LOWER         = 'δ'
        EPSILON_LOWER       = 'ε'
        ZETA_LOWER          = 'ζ'
        ETA_LOWER           = 'η'
        THETA_LOWER         = 'θ'
        IOTA_LOWER          = 'ι'
        KAPPA_LOWER         = 'κ'
        LAMBDA_LOWER        = 'λ'
        MU_LOWER            = 'μ'
        NU_LOWER            = 'ν'
        XI_LOWER            = 'ξ'
        OMICRON_LOWER       = 'ο'
        PI_LOWER            = 'π'
        RHO_LOWER           = 'ρ'
        SIGMA_LOWER_FINAL   = 'ς'  # Final sigma
        SIGMA_LOWER         = 'σ'
        TAU_LOWER           = 'τ'
        UPSILON_LOWER       = 'υ'
        PHI_LOWER           = 'φ'
        CHI_LOWER           = 'χ'
        PSI_LOWER           = 'ψ'
        OMEGA_LOWER         = 'ω'

    class misc(Enum, metaclass=DirectValueEnumMeta):
        # Miscellaneous Greek Symbols
        THETA_SYMBOL        = 'ϑ'
        PHI_SYMBOL          = 'ϕ'
        PI_SYMBOL           = 'ϖ'
        KAI_SYMBOL          = 'ϗ'
        SAMPI               = 'Ϡ'

# ------------------------------------------------------------------------------------
# RUNIC SYMBOLS
# ------------------------------------------------------------------------------------
class RUNIC(Enum, metaclass=DirectValueEnumMeta):
    '''
    Runic symbols.
    
    '''
    class OLD_NORSE(Enum, metaclass=DirectValueEnumMeta):
        '''
        Old Norse runeic scripts.
        
        '''
        class Elder_Futhark(Enum, metaclass=DirectValueEnumMeta):
            FEHU      = 'ᚠ'
            URUZ      = 'ᚢ'
            THURISAZ  = 'ᚦ'
            ANSUZ     = 'ᚨ'
            RAIDHO    = 'ᚱ'
            KENAZ     = 'ᚲ'
            GEBO      = 'ᚷ'
            WUNJO     = 'ᚹ'
            HAGALAZ   = 'ᚺ'
            NAUDIZ    = 'ᚾ'
            ISA       = 'ᛁ'
            JERA      = 'ᛃ'
            EIHWAZ    = 'ᛇ'
            PERTHRO   = 'ᛈ'
            ALGIZ     = 'ᛉ'
            SOWILO    = 'ᛊ'
            TIWAZ     = 'ᛏ'
            BERKANO   = 'ᛒ'
            EHWAZ     = 'ᛖ'
            MANNAZ    = 'ᛗ'
            LAGUZ     = 'ᛚ'
            INGWAZ    = 'ᛜ'
            DAGAZ     = 'ᛞ'
            OTHALA    = 'ᛟ'
        class Younger_Futhark(Enum, metaclass=DirectValueEnumMeta):
            FE        = 'ᚠ'
            UR        = 'ᚢ'
            THURS     = 'ᚦ'
            AS        = 'ᚬ'
            REID      = 'ᚱ'
            KAUN      = 'ᚴ'
            HAGALL    = 'ᚼ'
            NAUDR     = 'ᚾ'
            IS        = 'ᛁ'
            AR        = 'ᛅ'
            SOL       = 'ᛋ'
            TIU       = 'ᛐ'
            BJARKAN   = 'ᛒ'
            MADHR     = 'ᛘ'
            LOGR      = 'ᛚ'
            YR        = 'ᛦ'
        class Anglo_Saxon_Futhorc(Enum, metaclass=DirectValueEnumMeta):
            FEH       = 'ᚠ'
            UR        = 'ᚢ'
            THORN     = 'ᚦ'
            OS        = 'ᚩ'
            RAD       = 'ᚱ'
            CEN       = 'ᚳ'
            GYFU      = 'ᚷ'
            WYNN      = 'ᚹ'
            HAEGEL    = 'ᚻ'
            NYD       = 'ᚾ'
            IS        = 'ᛁ'
            GER       = 'ᛄ'
            EO        = 'ᛇ'
            PEORD     = 'ᛈ'
            EOLH      = 'ᛉ'
            SIGEL     = 'ᛋ'
            TIW       = 'ᛏ'
            BEORC     = 'ᛒ'
            EH        = 'ᛖ'
            MANN      = 'ᛗ'
            LAGU      = 'ᛚ'
            ING       = 'ᛝ'
            DAEG      = 'ᛞ'
            ODAL      = 'ᛟ'
            AESC      = 'ᚫ'

        # ELDER_FUTHARK       = Elder_Futhark
        # YOUNGER_FUTHARK     = Younger_Futhark
        # ANGLO_SAXON_FUTHORC = Anglo_Saxon_Futhorc

# ------------------------------------------------------------------------------------
# LOGOGRAPHIC SYMBOLS
# ------------------------------------------------------------------------------------
class LOGOGRAPHIC(Enum, metaclass=DirectValueEnumMeta):
    class ANCIENT_EGYPTIAN(Enum, metaclass=DirectValueEnumMeta):
        '''
        Enum for Ancient Egyptian hieroglyphs.
        
        '''
        class symbols(Enum, metaclass=DirectValueEnumMeta):
            # Example Egyptian Hieroglyph Symbols (Replace with actual hieroglyph codes)
            ANKH            = '\U00013000'  # Ankh
            WAS_SCEPTER     = '\U00013001'  # Was scepter
            DJED            = '\U00013002'  # Djed pillar
            SCARAB          = '\U00013003'  # Scarab
            SESHESHET       = '\U00013004'  # Sesheshet
            BA_BIRD         = '\U00013005'  # Ba bird
            CARTOUCHE       = '\U00013006'  # Cartouche
            LOTUS_FLOWER    = '\U00013007'  # Lotus flower
            SUN_DISC        = '\U00013008'  # Sun disc
            EYE_OF_HORUS    = '\U00013009'  # Eye of Horus
            FALCON          = '\U0001300A'  # Falcon
            URAEUS          = '\U0001300B'  # Uraeus (rearing cobra)
            CROOK_AND_FLAIL = '\U0001300C'  # Crook and flail
            VULTURE         = '\U0001300D'  # Vulture
            SISTRUM         = '\U0001300E'  # Sistrum
            MENAT           = '\U0001300F'  # Menat necklace
            SPHINX          = '\U00013010'  # Sphinx
            PALM_TREE       = '\U00013011'  # Palm tree
            WATER_RIPPLE    = '\U00013012'  # Water ripple
            PAPYRUS         = '\U00013013'  # Papyrus
            SHEN_RING       = '\U00013014'  # Shen ring
            OWL             = '\U00013015'  # Owl
            LION            = '\U00013016'  # Lion
            FEATHER         = '\U00013017'  # Feather of Ma'at
            COBRA           = '\U00013018'  # Cobra
            HIPPOPOTAMUS    = '\U00013019'  # Hippopotamus
            CROCODILE       = '\U0001301A'  # Crocodile
            HIEROGLYPH_A    = '\U0001301B'  # Hieroglyph 'A'
            HIEROGLYPH_B    = '\U0001301C'  # Hieroglyph 'B'
            HIEROGLYPH_C    = '\U0001301D'  # Hieroglyph 'C'

        class alphabetic(Enum, metaclass=DirectValueEnumMeta):
            # Alphabetic Hieroglyphs
            ALEPH           = '\U00013080'  # Hieroglyph for 'A'
            B              = '\U00013081'  # Hieroglyph for 'B'
            G              = '\U00013082'  # Hieroglyph for 'G'
            D              = '\U00013083'  # Hieroglyph for 'D'
            E              = '\U00013084'  # Hieroglyph for 'E'
            F              = '\U00013085'  # Hieroglyph for 'F'
            H              = '\U00013086'  # Hieroglyph for 'H'
            I              = '\U00013087'  # Hieroglyph for 'I'
            K              = '\U00013088'  # Hieroglyph for 'K'
            L              = '\U00013089'  # Hieroglyph for 'L'
            M              = '\U0001308A'  # Hieroglyph for 'M'
            N              = '\U0001308B'  # Hieroglyph for 'N'
            O              = '\U0001308C'  # Hieroglyph for 'O'
            P              = '\U0001308D'  # Hieroglyph for 'P'
            Q              = '\U0001308E'  # Hieroglyph for 'Q'
            R              = '\U0001308F'  # Hieroglyph for 'R'
            S              = '\U00013090'  # Hieroglyph for 'S'
            T              = '\U00013091'  # Hieroglyph for 'T'
            U              = '\U00013092'  # Hieroglyph for 'U'
            V              = '\U00013093'  # Hieroglyph for 'V'
            W              = '\U00013094'  # Hieroglyph for 'W'
            X              = '\U00013095'  # Hieroglyph for 'X'
            Y              = '\U00013096'  # Hieroglyph for 'Y'
            Z              = '\U00013097'  # Hieroglyph for 'Z'

        class logographic(Enum, metaclass=DirectValueEnumMeta):
            # Logographic Hieroglyphs
            PHARAOH         = '\U000132F0'  # Hieroglyph for 'Pharaoh'
            PYRAMID         = '\U000132F1'  # Hieroglyph for 'Pyramid'
            NILE            = '\U000132F2'  # Hieroglyph for 'Nile'
            GOD             = '\U000132F3'  # Hieroglyph for 'God'
            GODDESS         = '\U000132F4'  # Hieroglyph for 'Goddess'
            TEMPLE          = '\U000132F5'  # Hieroglyph for 'Temple'
            OBELISK         = '\U000132F6'  # Hieroglyph for 'Obelisk'
            TOMB            = '\U000132F7'  # Hieroglyph for 'Tomb'
            GOLD            = '\U000132F8'  # Hieroglyph for 'Gold'
            BREAD           = '\U000132F9'  # Hieroglyph for 'Bread'
            BEER            = '\U000132FA'  # Hieroglyph for 'Beer'
            HOUSE           = '\U000132FB'  # Hieroglyph for 'House'
            WATER           = '\U000132FC'  # Hieroglyph for 'Water'
            FISH            = '\U000132FD'  # Hieroglyph for 'Fish'
            FIELD           = '\U000132FE'  # Hieroglyph for 'Field'
            SHIP            = '\U000132FF'  # Hieroglyph for 'Ship'
            CHARIOT         = '\U00013300'  # Hieroglyph for 'Chariot'
            SUN             = '\U00013301'  # Hieroglyph for 'Sun'
            MOON            = '\U00013302'  # Hieroglyph for 'Moon'
            STAR            = '\U00013303'  # Hieroglyph for 'Star'
            HEAVEN          = '\U00013304'  # Hieroglyph for 'Heaven'
            EARTH           = '\U00013305'  # Hieroglyph for 'Earth'
            MOUNTAIN        = '\U00013306'  # Hieroglyph for 'Mountain'
            RIVER           = '\U00013307'  # Hieroglyph for 'River'
            LAKE            = '\U00013308'  # Hieroglyph for 'Lake'
            TREE            = '\U00013309'  # Hieroglyph for 'Tree'
            FLOWER          = '\U0001330A'  # Hieroglyph for 'Flower'
            ANIMAL          = '\U0001330B'  # Hieroglyph for 'Animal'
            BIRD            = '\U0001330C'  # Hieroglyph for 'Bird'
            FISC            = '\U0001330D'  # Hieroglyph for 'Fish'
            INSECT          = '\U0001330E'  # Hieroglyph for 'Insect'


# ------------------------------------------------------------------------------------
# CUNEIFORM SYMBOLS
# ------------------------------------------------------------------------------------
class CUNEIFORM(Enum, metaclass=DirectValueEnumMeta):
    '''
    Cuneiform symbols.
    
    '''
    class Sumerian(Enum, metaclass=DirectValueEnumMeta):
        '''
        Enum for Sumerian Cuneiform symbols.
        
        '''
        A               = '𒀀'
        AB              = '𒀊'
        AD              = '𒀜'
        AG              = '𒀝'
        AK              = '𒀭'
        AL              = '𒀸'
        AM              = '𒄠'
        AN              = '𒀭'
        AR              = '𒅈'
        ASH             = '𒀸'
        BA              = '𒁀'
        BAD             = '𒁁'
        BAR             = '𒁉'
        BI              = '𒁍'
        BU              = '𒁲'
        DA              = '𒁕'
        DAG             = '𒁕'
        DI              = '𒁺'
        DU              = '𒁺'
        E               = '𒂊'
        EN              = '𒂗'
        ER              = '𒂗'
        GA              = '𒂵'
        GAN             = '𒃲'
        GAR             = '𒃲'
        GI              = '𒄀'
        GID             = '𒄄'
        GIN             = '𒄄'
        GIR             = '𒄑'
        GISH            = '𒄑'
        GU              = '𒄖'
        GUD             = '𒄖'
        GUL             = '𒄖'
        HA              = '𒄩'
        HI              = '𒄭'
        HU              = '𒄷'
        I               = '𒅆'
        IB              = '𒅋'
        ID              = '𒅖'
        IM              = '𒅴'
        IN              = '𒅷'
        IR              = '𒅹'
        ISH             = '𒅻'
        KA              = '𒆠'
        KAK             = '𒆤'
        KI              = '𒆠'
        KU              = '𒆪'
        KUG             = '𒆬'
        KUR             = '𒆳'
        LAGAB           = '𒆸'
        LAGAR           = '𒆹'
        LAM             = '𒆷'
        LI              = '𒇷'
        LU              = '𒇻'
        LUM             = '𒇽'
        MA              = '𒌝'
        MASH            = '𒌝'
        ME              = '𒌝'
        MIN             = '𒌞'
        MU              = '𒌦'
        MUG             = '𒌧'
        MUNUS           = '𒌨'
        NA              = '𒈾'
        NE              = '𒉈'
        NIM             = '𒉌'
        NU              = '𒉡'
        PA              = '𒉺'
        PAD             = '𒉼'
        PAN             = '𒉽'
        PAP             = '𒉿'
        PI              = '𒊊'
        QA              = '𒋀'
        QI              = '𒋗'
        RA              = '𒊏'
        RI              = '𒊑'
        RU              = '𒊒'
        SA              = '𒊓'
        SAG             = '𒊕'
        SAL             = '𒊖'
        SAN             = '𒊗'
        SAR             = '𒊘'
        SHAR            = '𒊭'
        SHE             = '𒊺'
        SHU             = '𒋗'
        SI              = '𒋚'
        SIG             = '𒋛'
        SIGA            = '𒋜'
        SU              = '𒋢'
        SUD             = '𒋤'
        TA              = '𒋫'
        TAG             = '𒋬'
        TAR             = '𒋰'
        TE              = '𒋼'
        TI              = '𒋾'
        TIL             = '𒌁'
        TU              = '𒌅'
        TUM             = '𒌇'
        TUR             = '𒌉'
        U               = '𒌋'
        UD              = '𒌑'
        UM              = '𒌓'
        UN              = '𒌖'
        UR              = '𒌝'
        URU             = '𒌨'
        US              = '𒌫'
        UT              = '𒌰'
        UTU             = '𒌱'
        UZU             = '𒍑'
        ZA              = '𒍝'
        ZAG             = '𒍠'
        ZU              = '𒍪'
    class Akkadian(Enum, metaclass=DirectValueEnumMeta):
        '''
        Enum for Akkadian Cuneiform symbols.
        '''
        A               = '𒀀'
        AB              = '𒀊'
        AD              = '𒀜'
        AG              = '𒀝'
        AK              = '𒀭'
        AL              = '𒀸'
        AM              = '𒄠'
        AN              = '𒀭'
        AR              = '𒅈'
        ASH             = '𒀸'
        BA              = '𒁀'
        BAD             = '𒁁'
        BAR             = '𒁉'
        BI              = '𒁍'
        BU              = '𒁲'
        DA              = '𒁕'
        DAG             = '𒁕'
        DI              = '𒁺'
        DU              = '𒁺'
        E               = '𒂊'
        EN              = '𒂗'
        ER              = '𒂗'
        GA              = '𒂵'
        GAN             = '𒃲'
        GAR             = '𒃲'
        GI              = '𒄀'
        GID             = '𒄄'
        GIN             = '𒄄'
        GIR             = '𒄑'
        GISH            = '𒄑'
        GU              = '𒄖'
        GUD             = '𒄖'
        GUL             = '𒄖'
        HA              = '𒄩'
        HI              = '𒄭'
        HU              = '𒄷'
        I               = '𒅆'
        IB              = '𒅋'
        ID              = '𒅖'
        IM              = '𒅴'
        IN              = '𒅷'
        IR              = '𒅹'
        ISH             = '𒅻'
        KA              = '𒆠'
        KAK             = '𒆤'
        KI              = '𒆠'
        KU              = '𒆪'
        KUG             = '𒆬'
        KUR             = '𒆳'
        LAGAB           = '𒆸'
        LAGAR           = '𒆹'
        LAM             = '𒆷'
        LI              = '𒇷'
        LU              = '𒇻'
        LUM             = '𒇽'
        MA              = '𒌝'
        MASH            = '𒌝'
        ME              = '𒌝'
        MIN             = '𒌞'
        MU              = '𒌦'
        MUG             = '𒌧'
        MUNUS           = '𒌨'
        NA              = '𒈾'
        NE              = '𒉈'
        NIM             = '𒉌'
        NU              = '𒉡'
        PA              = '𒉺'
        PAD             = '𒉼'
        PAN             = '𒉽'
        PAP             = '𒉿'
        PI              = '𒊊'
        QA              = '𒋀'
        QI              = '𒋗'
        RA              = '𒊏'
        RI              = '𒊑'
        RU              = '𒊒'
        SA              = '𒊓'
        SAG             = '𒊕'
        SAL             = '𒊖'
        SAN             = '𒊗'
        SAR             = '𒊘'
        SHAR            = '𒊭'
        SHE             = '𒊺'
        SHU             = '𒋗'
        SI              = '𒋚'
        SIG             = '𒋛'
        SIGA            = '𒋜'
        SU              = '𒋢'
        SUD             = '𒋤'
        TA              = '𒋫'
        TAG             = '𒋬'
        TAR             = '𒋰'
        TE              = '𒋼'
        TI              = '𒋾'
        TIL             = '𒌁'
        TU              = '𒌅'
        TUM             = '𒌇'
        TUR             = '𒌉'
        U               = '𒌋'
        UD              = '𒌑'
        UM              = '𒌓'
        UN              = '𒌖'
        UR              = '𒌝'
        URU             = '𒌨'
        US              = '𒌫'
        UT              = '𒌰'
        UTU             = '𒌱'
        UZU             = '𒍑'
        ZA              = '𒍝'
        ZAG             = '𒍠'
        ZU              = '𒍪'

    # SUMERIAN = Sumerian
    # AKKADIAN = Akkadian

# ------------------------------------------------------------------------------------
# MATH SYMBOLS
# ------------------------------------------------------------------------------------
class MATHEMATICAL(Enum, metaclass=DirectValueEnumMeta):
    '''
    Enum for various mathematical symbols and their Unicode representations.
    
    '''
    # Mathematical Symbols
    INCREMENT                      = '∆'
    INFINITE                       = '∞'  # Changed from INFINITY
    PARTIAL_DIFFERENTIAL           = '∂'
    NABLA                          = '∇'
    ELEMENT_OF                     = '∈'
    NOT_ELEMENT_OF                 = '∉'  # Changed from NOT_AN_ELEMENT_OF
    SMALL_ELEMENT                  = '∊'  # Changed from SMALL_ELEMENT_OF
    CONTAINS_MEMBER                = '∋'  # Changed from CONTAINS_AS_MEMBER
    NOT_CONTAINS_MEMBER            = '∌'  # Changed from DOES_NOT_CONTAIN_AS_MEMBER
    N_ARY_PRODUCT                  = '∏'
    N_ARY_COPRODUCT                = '∐'
    N_ARY_SUMMATION                = '∑'
    MINUS_SIGN                     = '−'
    MINUS_OR_PLUS                  = '∓'  # Changed from MINUS_OR_PLUS_SIGN
    DOT_PLUS                       = '∔'
    DIVISION_SLASH                 = '∕'
    SET_MINUS                      = '∖'
    ASTERISK_OPERATOR              = '∗'
    RING_OPERATOR                  = '∘'
    BULLET_OPERATOR                = '∙'
    SQUARE_ROOT                    = '√'
    CUBE_ROOT                      = '∛'
    FOURTH_ROOT                    = '∜'
    CONSEQUENTLY                   = '∴'  # Changed from THEREFORE
    BECAUSE_OF                     = '∵'  # Changed from BECAUSE
    PROPORTIONAL_TO                = '∝'
    RIGHT_ANGLE                    = '∟'
    ANGLE                          = '∠'
    MEASURED_ANGLE                 = '∡'
    SPHERICAL_ANGLE                = '∢'
    DIVIDES                        = '∣'
    DOES_NOT_DIVIDE                = '∤'
    PARALLEL_TO                    = '∥'
    NOT_PARALLEL_TO                = '∦'
    LOGICAL_AND                    = '∧'
    LOGICAL_OR                     = '∨'
    INTERSECTION                   = '∩'
    UNION                          = '∪'
    INTEGRAL                       = '∫'
    DOUBLE_INTEGRAL                = '∬'
    TRIPLE_INTEGRAL                = '∭'
    CONTOUR_INTEGRAL               = '∮'
    SURFACE_INTEGRAL               = '∯'
    VOLUME_INTEGRAL                = '∰'
    CLOCKWISE_INTEGRAL             = '∱'
    CLOCKWISE_CONTOUR_INTEGRAL     = '∲'
    ANTICLOCKWISE_CONTOUR_INTEGRAL = '∳'

# ------------------------------------------------------------------------------------
# LOGICAL SYMBOLS
# ------------------------------------------------------------------------------------
